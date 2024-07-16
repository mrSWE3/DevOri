import asyncio
from typing import Dict, List, AsyncContextManager, Protocol, AsyncGenerator, Any

from paho.mqtt.client import topic_matches_sub
from utils import Subscriber, Subscribable, Message
from aiotools import TaskGroup # type: ignore has no stubs
from mqttDevices import Sender


def is_wild_topic(topic: str):
    return any(c in ("+","#") for c in topic)





class PhysicalClient[send_T, receive_T]( AsyncContextManager[Any], Protocol):
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


class FundementalClient[send_T, receive_T](AsyncContextManager[Any]): 
    def __init__(self, 
                 pysical_client: PhysicalClient[send_T, receive_T],
                 topic_prefix: str = "",
                 verbose: bool = False) -> None:
       
        self._prefix = topic_prefix
        self._pysical_client = pysical_client
        self._spesifict_subs: Dict[str, List[Subscriber[receive_T]]] = {}
        self._wildcard_subs: Dict[str, List[Subscriber[receive_T]]] = {}
        self.__tg = TaskGroup()
        self.verbose = verbose
    

    
    def _full_topic(self, end: str):
        return f"{self._prefix}/{end}"

    async def sub_topic(self, topic: str,subscriber: Subscriber[receive_T]) -> None:
        if not topic in (list(self._spesifict_subs.keys()) + list(self._wildcard_subs.keys())):
            await self._pysical_client.subscribe(topic= self._full_topic(topic))
            if self.verbose:
                print(f"New mqtt subscription: {self._full_topic(topic)}")

        has_wildcard = is_wild_topic(topic)
        if not has_wildcard:
            topic_subs = self._spesifict_subs.get(self._full_topic(topic), [])
            topic_subs.append(subscriber)
            self._spesifict_subs[self._full_topic(topic)] = topic_subs
            if self.verbose:
                print(f"Subscriber added to static topic: {self._full_topic(topic)}")
        else:
            topic_subs = self._wildcard_subs.get(self._full_topic(topic), [])
            topic_subs.append(subscriber)
            self._wildcard_subs[self._full_topic(topic)] = topic_subs
            print(f"Subscriber added to wildcard topic: {self._full_topic(topic)}")
            
    
    async def unsub_topic(self, topic: str, subscriber: Subscriber[receive_T]) -> None:
        
        if not is_wild_topic(topic):
            topic_subs = self._spesifict_subs.get(topic, None)
        else:
            topic_subs = self._wildcard_subs.get(topic, None)
            

        if topic_subs != None:
            try:
                topic_subs.remove(subscriber)
                if self.verbose:
                    print(f"Subscriber was removed from topic: {self._full_topic(topic)}")
                if len(topic_subs) == 0:
                    del self._spesifict_subs[topic]
                    await self._pysical_client.unsubscribe(topic= self._full_topic(topic))
                    if self.verbose:
                        print(f"Removed mqtt subscription from topic: {self._full_topic(topic)}")
            except ValueError:
                raise Exception(f"Subscriber not subscribed to this topic: {topic}")
        else:
            raise Exception(f"No subscribers of topic: {topic}")
        
            
    

    async def __listen(self):  # Always running as own task
        async for msg in self._pysical_client.get_receive_message_generator():
            if self.verbose:
                print(f"Recived message with payload: {msg.payload}, on topic: {msg.topic}")
            mesage_topic = msg.topic
            subscribers = self._spesifict_subs.get(msg.topic, [])
            for wild_topic, subs in self._wildcard_subs.items():
                if topic_matches_sub(wild_topic, mesage_topic):
                    subscribers.extend(subs)

            for sub in subscribers:
                if self.verbose:
                    print(f"Called back subscriber: {sub} of topic: {msg.topic}")
                t = sub.call_back(msg.payload)
                self.__tg.create_task(t)  # type: ignore
         

    async def __aenter__(self):
        await self.__tg.__aenter__()
        await self._pysical_client.__aenter__()
        self._remote_listener_task = asyncio.create_task(self.__listen())
        if self.verbose:
            print("Entered async context")
        return self
    

    async def __aexit__(self,*exc_info: Any):
        await self.__tg.__aexit__(*exc_info) # type: ignore
        await self._pysical_client.__aexit__(*exc_info)
        self._remote_listener_task.cancel()
        if self.verbose:
            print("Exited async context")
        return None
  

    async def publish(self, topic: str, payload: send_T) -> None:  
        c = self._pysical_client.publish(topic=self._full_topic(topic), payload=payload)
        self.__tg.create_task(c)  # type: ignore
        if self.verbose:
            print(f"Published to {self._full_topic(topic)} with payload {payload}")


    

class DeviceClient[send_T, receive_T]( Subscribable[receive_T, str, str], Sender[send_T]):
    def __init__(self, client: FundementalClient[send_T, receive_T], ) -> None:
        self._client = client

    async def subscribe(self, sub: Subscriber[receive_T], args: str) -> None:
        await self._client.sub_topic(args, sub)

    async def unsubscribe(self, sub: Subscriber[receive_T], args: str) -> None:
        await self._client.unsub_topic(args, sub)

    async def send(self, topic: str, payload: send_T):
        await self._client.publish(topic, payload)

    async def __aenter__(self):
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self,*exc_info: Any):
        await self._client.__aexit__(*exc_info)
        return None
