from __future__ import annotations

from typing import TypeVar, Generic, List, Dict, Any, Generator, AsyncContextManager, Protocol, Callable, Coroutine
import asyncio
import json
from dataclasses import dataclass


class Subscribable[subable_T, sub_args, unsub_args](Protocol):
    def __init__(self) -> None:
        super().__init__()
    async def subscribe(self, sub: Subscriber[subable_T], args: sub_args) -> None:
        pass
    async def unsubscribe(self, sub: Subscriber[subable_T], args: unsub_args) -> None:
        pass


class Subscriber[sub_T](Protocol):
    async def call_back(self, t: sub_T):
       ...

class LambdaSubscriber[sub_T](Subscriber[sub_T]):
    def __init__(self, call_back: Callable[[sub_T],Coroutine[None, None, None]]) -> None:
        super().__init__()
        self._call_back = call_back
    async def call_back(self, t: sub_T):
        await self._call_back(t)


def make_sub[sub_T](call_back: Callable[[sub_T],None]):
    return 

class QueueSubscriber[sub_T]:
    def __init__(self, max_itmes: int = 0) -> None:
        self._call_items: asyncio.Queue[sub_T] = asyncio.Queue(max_itmes)
    async def call_back(self, t: sub_T):
        if self._call_items.full():
            self._call_items.get_nowait()
        
        self._call_items.put_nowait(t)
    async def get_item(self) -> sub_T:
        return await self._call_items.get()
    
    def get_untill_empty(self) -> Generator[sub_T, None,  None]:
        while not self._call_items.empty():
            yield self._call_items.get_nowait()



def dict2bytes(d: Dict[Any, Any]) -> bytes:
    return json.dumps(d).encode('utf-8')

def bytes2dict(b: bytes) -> Dict[str, str | int | float]:
    return json.loads(b)


sub_AsyncContextManager = TypeVar("sub_AsyncContextManager", bound=AsyncContextManager[Any])
class MultiACM(AsyncContextManager[Any], Generic[sub_AsyncContextManager]):
    def __init__(self, resources: List[sub_AsyncContextManager]):
        self.resources: List[sub_AsyncContextManager] = resources

    async def __aenter__(self):
        self.active_resources = await asyncio.gather(*[resource.__aenter__() for resource in self.resources])
        return self

    async def __aexit__(self,*exc_info: Any):
        await asyncio.gather(*[resource.__aexit__(*exc_info) for resource in self.resources])


@dataclass
class Message[receive_T]:
    topic: str
    payload: receive_T