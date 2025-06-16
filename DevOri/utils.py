from typing import List, Any, AsyncContextManager, Protocol, Callable, Coroutine
import asyncio
import json
from dataclasses import dataclass

class Subscriber[item_T](Protocol):
    """
    ## Summary
        Generic object to use for async call backs
    ## Type Params
        item_T: type of item the subscriber can receive
    """
    
    async def call_back(self, item: item_T):
        """
        ## Summary
            Give subscriber an item to handle
        ## Args:
            item (item_T): item
        """
        ...
class Subscribable[item_T, sub_args, unsub_args](Protocol):
    """
    ## Summary    
        Generic interface for adding and removing subscribers in async
    ## Generics:
        item_T: type of item which can be sent to its subscribers
        sub_args: type of argument needed for subscribing
        unsub_args: type of argument needed to unsubscribe
    """

    def __init__(self) -> None:
        super().__init__()

    async def subscribe(self, sub: Subscriber[item_T], args: sub_args) -> None:
        """
        ## Summary:
            Subscribe subscriber to this object
        ## Args:
            sub (Subscriber[item_T]): the subscriber
            args (sub_args): the arguments with which the subscriber will be subscribed
        """
        ...

    async def unsubscribe(self, sub: Subscriber[item_T], args: unsub_args) -> None:
        """
        ## Summary
            Unsubscribe subscriber from this object
        ## Args:
            sub (Subscriber[item_T]): the subscriber
            args (unsub_args): the arguments with which the subscriber will be unsubscribed
        """
        ...

class LambdaSubscriber[item_T](Subscriber[item_T]):
    """
    ## Summary
        Subscriber with injected callback
    ## Type Params
        item_T: type of item the subscriber can receive
    """

    def __init__(self, call_back: Callable[[item_T],Coroutine[None, None, None]]) -> None:
        """
        ## Args
            call_back (Callable[[item_T], Coroutine[None, None, None]]): the method which will be called in place of this methods callback
        """
        super().__init__()
        self._call_back = call_back

    async def call_back(self, item: item_T):
        await self._call_back(item)


class QueueSubscriber[sub_T](Subscriber[sub_T]):
    """
    ## Summary
        A subscriber which queues its callback
    ## Type Params
        sub_T: 
    """
    def __init__(self, max_items: int = 0) -> None:
        """
        ## Args
            max_items (int): maximum number of queued callback items
        """
        self._call_items: asyncio.Queue[sub_T] = asyncio.Queue(max_items)
        
    async def call_back(self, item: sub_T):
        if self._call_items.full():
            self._call_items.get_nowait()
        self._call_items.put_nowait(item)

    async def get_item(self) -> sub_T:
        """
        ## Summary
            Get oldest callback item
        ## Return
            sub_T
        """
        return await self._call_items.get()

def any2bytes(d: Any) -> bytes:
    """
    ## Summary
        Serialize object 
    ## Args
        d (Any): object
    ## Return
        bytes: serialized object
    """
    return json.dumps(d).encode('utf-8')

def bytes2any(b: bytes) -> Any:
    """
    ## Summary
        Un-serialize object 
    ## Args
        b (bytes): the serialized object
    ## Return
        Any: the object
    """
    s = b.decode('utf-8')
    return json.loads(s)


class MultiACM[ACM_T](AsyncContextManager[List[ACM_T]]):
    """
    ## Summary
        Object to handel a list of AsyncContextManager as a single AsyncContextManager
    ## Type Params
        ACM_T: type of AsyncContextManager in list
    """
    def __init__(self, resources: List[AsyncContextManager[ACM_T]]):
        self.resources: List[AsyncContextManager[ACM_T]] = resources

    async def __aenter__(self):
        self.active_resources = await asyncio.gather(*[resource.__aenter__() for resource in self.resources])
        return self.active_resources

    async def __aexit__(self,*exc_info: Any):
        await asyncio.gather(*[resource.__aexit__(*exc_info) for resource in self.resources])


@dataclass
class Message[receive_T]:
    """
    ## Summary
        Mqtt message
    ## Type Params
        receive_T: payload type
    """
    topic: str
    payload: receive_T



