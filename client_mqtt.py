from __future__ import annotations

import asyncio
from typing import Callable, Dict, List, Generic, TypeVar, Coroutine, Generator, Tuple, AsyncContextManager, Protocol, AsyncGenerator
from types import AsyncGeneratorType
from aiomqtt import Client as AiomqttClient, Message
import uuid
from paho.mqtt.client import topic_matches_sub
from utils import Subscriber, Subscribable, MultiACM
from aiotools import TaskGroup
from mqttDevices import Sender, Publisher, Reciver, DualDevice



def is_wild_topic(topic: str):
    return any([c == "+" or c == "#" for c in topic])
send_T = TypeVar("send_T", contravariant=True)
receive_T = TypeVar("receive_T", covariant=True)
class PhysicalClient(Generic[send_T, receive_T], AsyncContextManager, Protocol):
    def __init__(self, *args, **kwargs) -> None:
        ...
    async def subscribe(self, topic: str):
        ...
    async def unsubscribe(self, topic: str):
        ...
    async def publish(self, topic: str, payload:send_T):
        ...
    def get_receive_message_generator(self) -> AsyncGenerator[receive_T, None]:
        ...
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

class AiomqttPhysicalClient(PhysicalClient[bytes, Message]):
    def __init__(self, aiomqttClient: AiomqttClient) -> None:
        self._aiomqttClient = aiomqttClient
    async def subscribe(self, topic: str):
        await self._aiomqttClient.subscribe(topic)
    async def unsubscribe(self, topic: str):
        await self._aiomqttClient.unsubscribe(topic)
    async def publish(self, topic: str, payload: bytes):
        await self._aiomqttClient.publish(topic, payload)
    def get_receive_message_generator(self) -> AsyncGenerator[Message, None]:
        return self._aiomqttClient.messages
    async def __aenter__(self):
        await self._aiomqttClient.__aenter__()
        return self
    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._aiomqttClient.__aexit__(exc_type, exc_value, traceback)
        return None


class FundementalClient(AsyncContextManager): 
    def __init__(self, 
                 pysical_client: PhysicalClient,
                 topic_prefix: str = "",
                 verbose: bool = False) -> None:
       
        self.prefix = topic_prefix
        self.pysical_client = pysical_client
        self.spesifict_subs: Dict[str, List[Subscriber[Message]]] = {}
        self.wildcard_subs: Dict[str, List[Subscriber[Message]]] = {}
        self.tg = TaskGroup()
        self.verbose = verbose
    

    
    def full_topic(self, end):
        return f"{self.prefix}/{end}"

    async def sub_topic(self, topic: str,subscriber: Subscriber[Message]) -> None:
        if not topic in (list(self.spesifict_subs.keys()) + list(self.spesifict_subs.keys())):
            await self.pysical_client.subscribe(topic= self.full_topic(topic))
            if self.verbose:
                print(f"New mqtt subscription: {self.full_topic(topic)}")

        has_wildcard = is_wild_topic(topic)
        if not has_wildcard:
            topic_subs = self.spesifict_subs.get(self.full_topic(topic), [])
            topic_subs.append(subscriber)
            self.spesifict_subs[self.full_topic(topic)] = topic_subs
            if self.verbose:
                print(f"Subscriber added to static topic: {self.full_topic(topic)}")
        else:
            topic_subs = self.wildcard_subs.get(self.full_topic(topic), [])
            topic_subs.append(subscriber)
            self.wildcard_subs[self.full_topic(topic)] = topic_subs
            print(f"Subscriber added to wildcard topic: {self.full_topic(topic)}")
            
    
    async def unsub_topic(self, topic: str,subscriber: Subscriber[Message]) -> None:
        
        if not is_wild_topic(topic):
            topic_subs = self.spesifict_subs.get(topic, None)
        else:
            topic_subs = self.wildcard_subs.get(topic, None)
            

        if topic_subs != None:
            try:
                topic_subs.remove(subscriber)
                if self.verbose:
                    print(f"Subscriber was removed from topic: {self.full_topic(topic)}")
                if len(topic_subs) == 0:
                    del self.spesifict_subs[topic]
                    await self.pysical_client.unsubscribe(topic= self.full_topic(topic))
                    if self.verbose:
                        print(f"Removed mqtt subscription from topic: {self.full_topic(topic)}")
            except ValueError:
                raise Exception(f"Subscriber not subscribed to this topic: {topic}")
        else:
            raise Exception(f"No subscribers of topic: {topic}")
        
            
    

    async def __listen(self):  # Always running as own task
        async for msg in self.pysical_client.get_receive_message_generator():
            if self.verbose:
                print(f"Recived message with payload: {msg.payload}, on topic: {msg.topic.value}")
            mesage_topic = msg.topic.value
            subscribers = self.spesifict_subs.get(msg.topic.value, [])
            for wild_topic, subs in self.wildcard_subs.items():
                if topic_matches_sub(wild_topic, mesage_topic):
                    subscribers.extend(subs)

            for sub in subscribers:
                if self.verbose:
                    print(f"Called back subscriber: {sub} of topic: {msg.topic.value}")
                self.tg.create_task(sub.call_back(msg))  # Prevent tasks from disappearing
         

    async def __aenter__(self):
        await self.tg.__aenter__()
        await self.pysical_client.__aenter__()
        self._remote_listener_task = asyncio.create_task(self.__listen())
        if self.verbose:
            print("Entered async context")
        return self
    

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.tg.__aexit__(exc_type, exc_value, traceback)
        await self.pysical_client.__aexit__(exc_type, exc_value, traceback)
        self._remote_listener_task.cancel()
        if self.verbose:
            print("Exited async context")
        return None
  

    async def publish(self, topic: str, payload: bytes) -> None:  # For type-safety
        c = self.pysical_client.publish(topic=self.full_topic(topic), payload=payload)
        self.tg.create_task(c) 
        print(f"Published to {self.full_topic(topic)} with payload {payload}")


    

class DeviceClient(Subscribable[Message, str, str], Sender[bytes]):
    def __init__(self, client: FundementalClient, ) -> None:
        self.client = client

    async def subscribe(self, sub: Subscriber[Message], args: str) -> None:
        await self.client.sub_topic(args, sub)

    async def unsubscribe(self, sub: Subscriber[Message], args: str) -> None:
        await self.client.unsub_topic(args, sub)

    async def send(self, topic: str, payload: bytes):
        await self.client.publish(topic, payload)

    async def __aenter__(self):
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.client.__aexit__(exc_type, exc_value, traceback)
        return None
