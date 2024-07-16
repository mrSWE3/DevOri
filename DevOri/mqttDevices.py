
import asyncio
from typing import AsyncContextManager, Dict, Protocol, Any, List, Coroutine, LiteralString, Callable, Type
from utils import Subscribable, LambdaSubscriber
from enum import Enum

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



class Publisher[receive_T, valid_topics: LiteralString, e: Enum](AsyncContextManager[Any]):
    def __init__(self, friendly_name: str, 
                 informer: Subscribable[receive_T, str, str],
                 category_sorters: Dict[valid_topics, Callable[[receive_T], e]],
                 categories: Type[e],
                 prefix: str = ""
                 ) -> None:
        
        self._category_sorters = category_sorters
        self._topic_categories: Dict[valid_topics, Dict[e, asyncio.Queue[receive_T]]] = {}
        self._subscribers: Dict[valid_topics, LambdaSubscriber[receive_T]] = {}
        self._informer: Subscribable[receive_T, str, str] = informer
        self.prefix = f"{prefix}{"/" if prefix != "" else ""}{friendly_name}"

        for topic in self._category_sorters.keys():
            self._topic_categories[topic] = {}
            for category in categories:
                self._topic_categories[topic][category] = asyncio.Queue[receive_T]()

    def make_sub(self, topic: valid_topics) -> LambdaSubscriber[receive_T]:
        async def f(payload: receive_T):
            category = self._category_sorters[topic](payload)
            await self._topic_categories[topic][category].put(payload)
        return LambdaSubscriber[receive_T](f)

    async def __aenter__(self):
        tasks: List[Coroutine[Any, Any, None]] = []
        
        
        for topic in self._category_sorters.keys():
            sub = self.make_sub(topic)
            self._subscribers[topic] = sub
            tasks.append(self._informer.subscribe(sub, 
                                                  f"{self.prefix}{"/" if topic != "" else ""}{topic}"))
        await asyncio.gather(*tasks)
        return self
    
    async def recive_from(self, topic: valid_topics, category: e) -> receive_T:
        if not (topic in self._topic_categories.keys()):
            raise Exception("Topic is not subscribed to, call could never finish")
        return await self._topic_categories[topic][category].get()
        
    
    async def __aexit__(self,*exc_info: Any):
        tasks: List[Coroutine[Any, Any, None]] = []
        for topic in self._category_sorters.keys():
            sub = self._subscribers[topic]
            tasks.append(self._informer.unsubscribe(sub, f"{self.prefix}/{topic}"))
        await asyncio.gather(*tasks)

class Communicator[payload_T, receive_T](Sender[payload_T], Subscribable[receive_T, str, str], Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()

class Device[payload_T, receive_T, valid_topics: LiteralString, e: Enum]( AsyncContextManager[Any]):
    def __init__(self, friendly_name: str,
                 communicator: Communicator[payload_T, receive_T],
                 category_sorters: Dict[valid_topics, Callable[[receive_T], e]],
                 categories: Type[e],
                 prefix: str = ""
                 ) -> None:
        self._reciver = Reciver[payload_T](friendly_name, communicator, prefix)
        self._publisher = Publisher[receive_T, valid_topics, e](
            friendly_name, communicator, category_sorters,categories, prefix)

    async def send_to(self, topic: LiteralString, payload: payload_T):
        await self._reciver.send_to(topic, payload)
        
    
    async def recive_from(self, topic: valid_topics, category: e) -> receive_T:
        return await self._publisher.recive_from(topic, category)

    async def __aenter__(self):
        await self._publisher.__aenter__()
        return self

   
    async def __aexit__(self,*exc_info: Any):
        await self._publisher.__aexit__(*exc_info)
        return None