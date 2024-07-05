from __future__ import annotations

import asyncio
from typing import Dict, List, Generic, TypeVar, AsyncContextManager, Protocol, AsyncGenerator, Any

from paho.mqtt.client import topic_matches_sub
from utils import Subscriber, Subscribable, Message
from aiotools import TaskGroup # type: ignore has no stubs
from mqttDevices import Sender


def is_wild_topic(topic: str):
    return any([c == "+" or c == "#" for c in topic])


send_T = TypeVar("send_T", contravariant=True)
receive_T = TypeVar("receive_T")



class PhysicalClient(Generic[send_T, receive_T], AsyncContextManager[Any], Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...
    async def subscribe(self, topic: str):
        ...
    async def unsubscribe(self, topic: str):
        ...
    async def publish(self, topic: str, payload: send_T):
        ...
    def get_receive_message_generator(self) -> AsyncGenerator[Message[receive_T], None]:
        ...
    async def __aenter__(self):
        return self
    async def __aexit__(self,*exc_info: Any):
        return None


class FundementalClient(AsyncContextManager[Any], Generic[send_T, receive_T]): 
    def __init__(self, 
                 pysical_client: PhysicalClient[send_T, receive_T],
                 topic_prefix: str = "",
                 verbose: bool = False) -> None:
       
        self.prefix = topic_prefix
        self.pysical_client = pysical_client
        self.spesifict_subs: Dict[str, List[Subscriber[receive_T]]] = {}
        self.wildcard_subs: Dict[str, List[Subscriber[receive_T]]] = {}
        self.tg = TaskGroup()
        self.verbose = verbose
    

    
    def full_topic(self, end: str):
        return f"{self.prefix}/{end}"

    async def sub_topic(self, topic: str,subscriber: Subscriber[receive_T]) -> None:
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
                print(f"Subscriber addedrequestign to static topic: {self.full_topic(topic)}")
        else:
            topic_subs = self.wildcard_subs.get(self.full_topic(topic), [])
            topic_subs.append(subscriber)
            self.wildcard_subs[self.full_topic(topic)] = topic_subs
            print(f"Subscriber added to wildcard topic: {self.full_topic(topic)}")
            
    
    async def unsub_topic(self, topic: str,subscriber:  Subscriber[receive_T]) -> None:
        
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
                print(f"Recived message with payload: {msg.payload}, on topic: {msg.topic}")
            mesage_topic = msg.topic
            subscribers = self.spesifict_subs.get(msg.topic, [])
            for wild_topic, subs in self.wildcard_subs.items():
                if topic_matches_sub(wild_topic, mesage_topic):
                    subscribers.extend(subs)

            for sub in subscribers:
                if self.verbose:
                    print(f"Called back subscriber: {sub} of topic: {msg.topic}")
                self.tg.create_task(sub.call_back(msg))  # type: ignore Prevent tasks from disappearing
         

    async def __aenter__(self):
        await self.tg.__aenter__()
        await self.pysical_client.__aenter__()
        self._remote_listener_task = asyncio.create_task(self.__listen())
        if self.verbose:
            print("Entered async context")
        return self
    

    async def __aexit__(self,*exc_info: Any):
        await self.tg.__aexit__(*exc_info) # type: ignore
        await self.pysical_client.__aexit__(*exc_info)
        self._remote_listener_task.cancel()
        if self.verbose:
            print("Exited async context")
        return None
  

    async def publish(self, topic: str, payload: send_T) -> None:  # For type-safety
        c = self.pysical_client.publish(topic=self.full_topic(topic), payload=payload)
        self.tg.create_task(c)  # type: ignore
        print(f"Published to {self.full_topic(topic)} with payload {payload}")


    
dc_receive_T = TypeVar("dc_receive_T") 
class DeviceClient(Generic[send_T, dc_receive_T], Subscribable[dc_receive_T, str, str], Sender[send_T]):
    def __init__(self, client: FundementalClient[send_T, dc_receive_T], ) -> None:
        self.client = client

    async def subscribe(self, sub: Subscriber[dc_receive_T], args: str) -> None:
        await self.client.sub_topic(args, sub)

    async def unsubscribe(self, sub: Subscriber[dc_receive_T], args: str) -> None:
        await self.client.unsub_topic(args, sub)

    async def send(self, topic: str, payload: send_T):
        await self.client.publish(topic, payload)

    async def __aenter__(self):
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self,*exc_info: Any):
        await self.client.__aexit__(*exc_info)
        return None
