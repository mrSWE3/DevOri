
import asyncio
from typing import AsyncContextManager, Dict, Protocol, Any, List, Coroutine, LiteralString, Callable, Type
from .utils import Subscribable, LambdaSubscriber
from enum import Enum

class Sender[payload_T](Protocol):
    """
    ## Summary
        Interface for for objects to send payloads to topics
    ## Type Params
        payload_T: type of payload
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None: 
        ...

    async def send(self, topic: str, payload: payload_T):
        """
        ## Summary
            Send payload to topic
        ## Args
            topic (str): topic to send payload to
            payload (payload_T): payload to send to topic
        """
        ...

class Communicator[payload_T, receive_T](Sender[payload_T], Subscribable[receive_T, str, str], Protocol):
    """
    ## Summary
        Interface for objects to be both Sender and Subscribable
    ## Type Params
        payload_T: type of payload which can be sent
        receive_T: type of payload which subscribers can receive
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None: 
        ...

class Receiver[payload_T, valid_topics: LiteralString]:
    """
    ## Summary
        An device which can receive payloads
    ## Type Params
        payload_T: type of payloads this object can send
        valid_topics (LiteralString): topics that the Receiver will accept messages on
    """
    def __init__(self, friendly_name: str, 
                 sender: Sender[payload_T],
                 prefix: str = ""
                 ) -> None:
        """
        ## Args
            friendly_name (str): friendly name of receiver
            sender (Sender[payload_T]): receiver's methods of sending messages
            prefix (str): static prefix of topics
        """
        self._friendly_name = friendly_name
        self._prefix = f"{prefix}{"/" if prefix != "" else ""}{friendly_name}"
        
        self._sender = sender

    async def send_to(self, topic: valid_topics, payload: payload_T):
        """
        ## Summary
            Sends a payload to a valid topic
        ## Args
            topic (valid_topics): the valid topic which the topic will be sent to
            payload (payload_T): the payload to be sent
        """
        await self._sender.send(f"{self._prefix}/{topic}", payload)

class Publisher[item_T, valid_topics: LiteralString, e: Enum](AsyncContextManager[Any]):
    """
    ## Summary
        An device which has items to give
    ## Type Params
        item_T: the type of the arguments it gives
        valid_topics (LiteralString): the topics from which items can be requested from
        e (Enum): the type of categories items 
    """
    def __init__(self, friendly_name: str, 
                 informer: Subscribable[item_T, str, str],
                 category_sorters: Dict[valid_topics, Callable[[item_T], e]],
                 categories: Type[e],
                 message_save_limit: Dict[valid_topics, Dict[e, int]] = {},
                 prefix: str = ""
                 ) -> None:
        """
        ## Args
            friendly_name (str): the friendly name of the Publisher
            informer (Subscribable[item_T, str, str]): the Subscribable to receive information form
            category_sorters (Dict[valid_topics, Callable[[item_T], e]]): methods to sort each item into a category for each valid topic. If not sorter is given, all items will be put under category None for that topic.
            message_save_limit (Dict[valid_topics, Dict[e, int]]): the maximum number of items saved on for each category for each valid topic. Unspecified amounts will note have limits.
            prefix (str): prefix of topics to receive items from
        """
        self._category_sorters = category_sorters
        self._topic_categories: Dict[valid_topics, Dict[e, asyncio.Queue[item_T]]] = {}
        self._subscribers: Dict[valid_topics, LambdaSubscriber[item_T]] = {}
        self._informer: Subscribable[item_T, str, str] = informer
        self.prefix = f"{prefix}{"/" if prefix != "" else ""}{friendly_name}"

        for topic in self._category_sorters.keys():
            topic_limit = message_save_limit.get(topic, {})
            self._topic_categories[topic] = {}
            for category in categories:
                limit = topic_limit.get(category, 0)
                self._topic_categories[topic][category] = asyncio.Queue[item_T](limit)
    async def receive_from(self, topic: valid_topics, category: e) -> item_T:
        """
        ## Summary
            Request to revive an item from a topic under a category
        ## Args
            topic (valid_topics): topic to receive from
            category (e): category under topic to receive from
        ## Return
            item_T: the item requested
        """
        if not (topic in self._topic_categories.keys()):
            raise Exception("Topic is not subscribed to, call could never finish")
        return await self._topic_categories[topic][category].get()
        
    def __make_sub(self, topic: valid_topics) -> LambdaSubscriber[item_T]:
        """
        ## Summary
            Private method. Creates a subscriber which wll given a payload on its topic
            will sort it into the correct category queue.
        ## Args
            topic (valid_topics): topic to for the subscriber to sort items on
        ## Return
            LambdaSubscriber[item_T]: the subscriber
        """
        async def f(payload: item_T):
            category = self._category_sorters[topic](payload)
            if self._topic_categories[topic][category].full():
                await self._topic_categories[topic][category].get()
            try: 
                self._topic_categories[topic][category].put_nowait(payload)
            except asyncio.QueueFull:
                pass
                
            
        return LambdaSubscriber[item_T](f)

    async def __aenter__(self):
        tasks: List[Coroutine[Any, Any, None]] = []
        
        
        for topic in self._category_sorters.keys():
            sub = self.__make_sub(topic)
            self._subscribers[topic] = sub
            tasks.append(self._informer.subscribe(sub, 
                                                  f"{self.prefix}{"/" if topic != "" else ""}{topic}"))
        await asyncio.gather(*tasks)
        return self
    
    async def __aexit__(self,*exc_info: Any):
        tasks: List[Coroutine[Any, Any, None]] = []
        for topic in self._category_sorters.keys():
            sub = self._subscribers[topic]
            tasks.append(self._informer.unsubscribe(sub, f"{self.prefix}/{topic}"))
        await asyncio.gather(*tasks)


class Device[payload_T, valid_send_topics: LiteralString, receive_T, valid_receive_topics: LiteralString, e: Enum]( AsyncContextManager[Any]):
    """
    ## Summary
        An device which can receive payloads and which has items to give
    ## Type Params
        payload_T: type of payloads which can be sent to device
        valid_send_topics (LiteralString): valid topic which payloads can be sent to
        receive_T: type of items which can be requested
        valid_receive_topics (LiteralString): valid topics items can be requested from
        e (Enum): the categories items are subdivided under
    """
    def __init__(self, friendly_name: str,
                 communicator: Communicator[payload_T, receive_T],
                 category_sorters: Dict[valid_receive_topics, Callable[[receive_T], e]],
                 categories: Type[e],
                 message_save_limit: Dict[valid_receive_topics, Dict[e, int]] = {},
                 prefix: str = ""
                 ) -> None:
        """
        ## Args
            friendly_name (str): the friendly name of the device
            communicator (Communicator[payload_T, receive_T]): 
            category_sorters (Dict[valid_receive_topics, Callable[[receive_T], e]]): 
            message_save_limit (Dict[valid_receive_topics, Dict[e, int]]): 
            prefix (str): 
        """

        self._receiver = Receiver[payload_T, valid_send_topics](friendly_name, communicator, prefix)
        self._publisher = Publisher[receive_T, valid_receive_topics, e](
            friendly_name, communicator, category_sorters,categories, message_save_limit, prefix)

    async def send_to(self, topic: valid_send_topics, payload: payload_T):
        """
        ## Summary
            Send payload to a valid topic
        ## Args
            topic (valid_send_topics): topic to send payload to
            payload (payload_T):  type of payload to send to topic
        """
        await self._receiver.send_to(topic, payload)
        
    
    async def receive_from(self, topic: valid_receive_topics, category: e) -> receive_T:
        """
        ## Summary
            Request to receive an item from a topic under a category
        ## Args
            topic (valid_receive_topics): topic to receive from
            category (e): category under topic to receive from
        ## Return
            receive_T: payload requested from topic under category
        """
        return await self._publisher.receive_from(topic, category)

    async def __aenter__(self):
        await self._publisher.__aenter__()
        return self

   
    async def __aexit__(self,*exc_info: Any):
        await self._publisher.__aexit__(*exc_info)
        return None