from __future__ import annotations

from typing import TypeVar, Generic, List, Dict, Any, Generator, AsyncContextManager, Protocol
import asyncio
import json
from dataclasses import dataclass

subable_T = TypeVar("subable_T", )
sub_args = TypeVar("sub_args", contravariant=True)
unsub_args = TypeVar("unsub_args", contravariant=True)
class Subscribable(Generic[subable_T, sub_args, unsub_args], Protocol):
    def __init__(self) -> None:
        super().__init__()
    async def subscribe(self, sub: Subscriber[subable_T], args: sub_args) -> None:
        pass
    async def unsubscribe(self, sub: Subscriber[subable_T], args: unsub_args) -> None:
        pass


sub_T = TypeVar("sub_T")
class Subscriber(Generic[sub_T]):
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



sub_AsyncContextManager = TypeVar("sub_AsyncContextManager", bound=AsyncContextManager[Any])
class MultiACM(AsyncContextManager[Any], Generic[sub_AsyncContextManager]):
    def __init__(self, resources: List[sub_AsyncContextManager]):
        self.resources: List[sub_AsyncContextManager] = resources

    async def __aenter__(self):
        self.active_resources = await asyncio.gather(*[resource.__aenter__() for resource in self.resources])
        return self

    async def __aexit__(self,*exc_info: Any):
        await asyncio.gather(*[resource.__aexit__(*exc_info) for resource in self.resources])

receive_T = TypeVar("receive_T")
@dataclass
class Message(Generic[receive_T]):
    topic: str
    payload: receive_T