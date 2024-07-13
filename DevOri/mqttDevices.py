
import asyncio
from typing import AsyncContextManager, Dict, Set, Protocol, Any, List, Coroutine, LiteralString
from utils import Subscribable, Subscriber



class Sender[payload_T](Protocol):
    def __init__(self) -> None:
        super().__init__()
    
    async def send(self, topic: str, payload: payload_T):
        pass


class Reciver[payload_T]:
    def __init__(self, friendly_name: str, 
                 sender: Sender[payload_T],
                 prefix: str = ""
                 ) -> None:
        self._friendly_name = friendly_name
        self._prefix = f"{prefix}{"/" if prefix != "" else ""}{friendly_name}"
        
        self._sender = sender

    async def send_to(self, topic: LiteralString, payload: payload_T):
        await self._sender.send(f"{self._prefix}/{topic}", payload)






class Publisher[receive_T](AsyncContextManager[Any]):
    def __init__(self, friendly_name: str, 
                 informer: Subscribable[receive_T, str, str],
                 read_topics: Set[str],
                 prefix: str = ""
                 ) -> None:
        self._subscribers: Dict[str, Subscriber[receive_T]] = {}
        self._informer: Subscribable[receive_T, str, str] = informer
        self._publish_topics: Set[str] = read_topics
        
        self.prefix = f"{prefix}{"/" if prefix != "" else ""}{friendly_name}"

    async def __aenter__(self):
        tasks: List[Coroutine[Any, Any, None]] = []
        for topic in self._publish_topics:
            sub = Subscriber[receive_T]()
            self._subscribers[topic] = sub
            tasks.append(self._informer.subscribe(sub, 
                                                  f"{self.prefix}{"/" if topic != "" else ""}{topic}"))
        await asyncio.gather(*tasks)
        return self
    
    async def recive_from(self, topic: LiteralString) -> receive_T:
        if not (topic in self._publish_topics):
            raise Exception("Topic is not subscribed to, call could never finish")
        return (await self._subscribers[topic].get_item())
        
    
    async def __aexit__(self,*exc_info: Any):
        tasks: List[Coroutine[Any, Any, None]] = []
        for topic in self._publish_topics:
            sub = self._subscribers[topic]
            tasks.append(self._informer.unsubscribe(sub, f"{self.prefix}/{topic}"))
        await asyncio.gather(*tasks)

class Communicator[payload_T, receive_T](Sender[payload_T], Subscribable[receive_T, str, str], Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()

class Device[payload_T, receive_T]( AsyncContextManager[Any]):
    def __init__(self, friendly_name: str,
                 communicator: Communicator[payload_T, receive_T],
                 read_topics: Set[str],
                 prefix: str = ""
                 ) -> None:
        self._reciver = Reciver[payload_T](friendly_name, communicator, prefix)
        self._publisher = Publisher[receive_T](friendly_name, communicator, read_topics, prefix)

    async def send_to(self, topic: LiteralString, payload: payload_T):
        await self._reciver.send_to(topic, payload)
        
    
    async def recive_from(self, topic: LiteralString) -> receive_T:
        return await self._publisher.recive_from(topic)

    async def __aenter__(self):
        await self._publisher.__aenter__()
        return self

   
    async def __aexit__(self,*exc_info: Any):
        await self._publisher.__aexit__(*exc_info)
        return None