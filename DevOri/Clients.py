import asyncio
from typing import Dict, List, AsyncContextManager, Protocol, AsyncGenerator, Any

from paho.mqtt.client import topic_matches_sub
from .utils import Subscriber, Subscribable, Message
from aiotools import TaskGroup # type: ignore has no stubs
from .MqttDevices import Sender


def is_wild_topic(topic: str):
    """
    ## Summary
        Checks if topic is a wildcard
    ## Args
        topic (str): topic to be checked
    """
    return any(c in ("+","#") for c in topic)


class PhysicalClient[send_T, receive_T]( AsyncContextManager[Any], Protocol):
    """
    ## Summary
        Interface for the actual MQTT communication client. This interface connects the internal 
        device oriented representation with a real the real MQTT implementation. 
    ## Type Params
        send_T: type of payload to send to the client
        receive_T: type of payload to receive from the client
    """


    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...

    async def subscribe(self, topic: str):
        """
        ## Summary
            Subscribe to MQTT topic
        ## Args
            topic (str): topic to subscribe to
        """
        ...

    async def unsubscribe(self, topic: str):
        """
        ## Summary
            Unsubscribe to MQTT topic
        ## Args
            topic (str): topic to unsubscribe to
        """
        ...

    async def publish(self, topic: str, payload: send_T):
        """
        ## Summary
            Send payload to client. Make sure that this method does not run indefinitely.
        ## Args
            topic (str): topic to send to 
            payload (send_T): payload to send
        """
        ...

    def get_receive_message_generator(self) -> AsyncGenerator[Message[receive_T], None]:
        """
        ## Summary
            Returns the asynchronous message generator from which messages can be received
        ## Return
            AsyncGenerator[Message[receive_T], None]
        """
        ...

    async def __aenter__(self):
        return self
    
    async def __aexit__(self,*exc_info: Any) ->  None:
        return None


class FundamentalClient[send_T, receive_T](AsyncContextManager[Any]): 
    """
    ## Summary
        The core client of the library. Let's individual Subscriber objects 
        be notified of messages on specific topics.
    ## Type Params
        send_T: type of payload delivered to the client
        receive_T: type of payload delivered to subscribers
    """


    def __init__(self, 
                 physical_client: PhysicalClient[send_T, receive_T],
                 topic_prefix: str = "",
                 verbose: bool = False) -> None:
        """
        ## Args
            physical_client (PhysicalClient[send_T, receive_T]): client to handel actual MQTT communication
            topic_prefix (str): static prefix to all topics
            verbose (bool): if True, prints behavior
        """
        self._prefix = topic_prefix
        self._physical_client = physical_client
        self._specific_subs: Dict[str, List[Subscriber[receive_T]]] = {}
        self._wildcard_subs: Dict[str, List[Subscriber[receive_T]]] = {}

        #Private, do not access
        #Task group for reference to tasks until they finish
        #For now, tasks do not have a time to liv
        #Thus memory leak can occur if tasks are added which never end
        self.__tg = TaskGroup()
        self.verbose = verbose
    
    def _full_topic(self, end: str):
        """
        ## Summary
            Helper method for retrieving the full topic string including the defined prefix
        ## Args
            end (str): the end of the full topic
        """
        return f"{self._prefix}/{end}"

    async def sub_topic(self, topic: str,subscriber: Subscriber[receive_T]) -> None:
        """
        ## Summary
            Subscribes a subscriber to the given topic. Ones a message is received on 
            the topic, the subscriber will be notified.
        ## Args
            topic (str): topic to subscribe to
            subscriber (Subscriber[receive_T]): subscriber to be subscribed
        """
        if not topic in (list(self._specific_subs.keys()) + list(self._wildcard_subs.keys())):
            await self._physical_client.subscribe(topic= self._full_topic(topic))
            if self.verbose:
                print(f"New mqtt subscription: {self._full_topic(topic)}")

        has_wildcard = is_wild_topic(topic)
        if not has_wildcard:
            topic_subs = self._specific_subs.get(self._full_topic(topic), [])
            topic_subs.append(subscriber)
            self._specific_subs[self._full_topic(topic)] = topic_subs
            if self.verbose:
                print(f"Subscriber added to static topic: {self._full_topic(topic)}")
        else:
            topic_subs = self._wildcard_subs.get(self._full_topic(topic), [])
            topic_subs.append(subscriber)
            self._wildcard_subs[self._full_topic(topic)] = topic_subs
            print(f"Subscriber added to wildcard topic: {self._full_topic(topic)}")
            
    async def unsub_topic(self, topic: str, subscriber: Subscriber[receive_T]) -> None:
        """
        ## Summary
            Unsubscribes a subscriber to the given topic. Subscriber will no longer
            be notified of messages on this topic
        ## Args
            topic (str): 
            subscriber (Subscriber[receive_T]): 
        """
        if not is_wild_topic(topic):
            topic_subs = self._specific_subs.get(topic, None)
        else:
            topic_subs = self._wildcard_subs.get(topic, None)
            

        if topic_subs != None:
            try:
                topic_subs.remove(subscriber)
                if self.verbose:
                    print(f"Subscriber was removed from topic: {self._full_topic(topic)}")
                if len(topic_subs) == 0:
                    del self._specific_subs[topic]
                    await self._physical_client.unsubscribe(topic= self._full_topic(topic))
                    if self.verbose:
                        print(f"Removed mqtt subscription from topic: {self._full_topic(topic)}")
            except ValueError:
                if self.verbose:
                    print(f"Subscriber not subscribed to this topic: {topic}, can not be removed")
        else:
            if self.verbose:
               print(f"Subscriber not subscribed to this topic: {topic}, can not be removed")
        
    async def __listen(self):
        """
        ## Summary
            Private method, do not call. This method notifies subscribers of 
            messages received on their subscriber topics.
        """
        async for msg in self._physical_client.get_receive_message_generator():
            if self.verbose:
                print(f"Recived message with payload: {msg.payload}, on topic: {msg.topic}")
            mesage_topic = msg.topic
            subscribers = self._specific_subs.get(msg.topic, [])
            for wild_topic, subs in self._wildcard_subs.items():
                if topic_matches_sub(wild_topic, mesage_topic):
                    subscribers.extend(subs)

            for sub in subscribers:
                if self.verbose:
                    print(f"Called back subscriber: {sub} of topic: {msg.topic}")
                t = sub.call_back(msg.payload)
                self.__tg.create_task(t)  # type: ignore
         

    async def __aenter__(self):
        """
        ## Summary
            Sets up the asynchronous context of the client
        """
        await self.__tg.__aenter__()
        await self._physical_client.__aenter__()
        self._remote_listener_task = asyncio.create_task(self.__listen())
        if self.verbose:
            print("Entered async context")
        return self
    
    async def __aexit__(self, *exc_info: Any):
        """
        ## Summary
            Tear down the asynchronous context of the client
        """
        await self.__tg.__aexit__(*exc_info) # type: ignore
        await self._physical_client.__aexit__(*exc_info)
        self._remote_listener_task.cancel()
        if self.verbose:
            print("Exited async context")
        return None
  
    async def publish(self, topic: str, payload: send_T) -> None:  
        """
        ## Summary
            Publish a payload to a topic. 
            Makes sure that the physical MQTT client finishes publishing,
            unless this object's context i exited.
        ## Args
            topic (str): topic to publish to
            payload (send_T): payload to publish
        """
        c = self._physical_client.publish(topic=self._full_topic(topic), payload=payload)
        self.__tg.create_task(c)  # type: ignore
        if self.verbose:
            print(f"Published to {self._full_topic(topic)} with payload {payload}")


    

class DeviceClient[send_T, receive_T](Subscribable[receive_T, str, str], Sender[send_T]):
    """i
    ## Summary
        Client used by Devices. Smple implementation of super types.
    ## Type Params
        send_T: type of arguments which can be sent to this client
        receive_T: type of item which will be sent back to subscribers 
    """

    def __init__(self, client: FundamentalClient[send_T, receive_T], ) -> None:
        """
        ## Args
            client (FundamentalClient[send_T, receive_T]): client to handel communication
        """
        self._client = client

    async def subscribe(self, sub: Subscriber[receive_T], args: str) -> None:
        """
        ## Summary
            Subscribe subscriber to topic
        ## Args
            sub (Subscriber[receive_T]): The subscriber to be subscribed
            args (str): the topic to be subscribed to
        """
        await self._client.sub_topic(args, sub)

    async def unsubscribe(self, sub: Subscriber[receive_T], args: str) -> None:
        """
        ## Summary
            Unsubscribe subscriber to topic
        ## Args
            sub (Subscriber[receive_T]): The subscriber to be unsubscribed
            args (str): the topic to be unsubscribed from
        """
        await self._client.unsub_topic(args, sub)

    async def send(self, topic: str, payload: send_T):
        """
        ## Summary
            Sends a payload to a topic
        ## Args
            topic (str): the topic to send to
            payload (send_T): the payload to send
        """
        await self._client.publish(topic, payload)

    async def __aenter__(self):
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self,*exc_info: Any):
        await self._client.__aexit__(*exc_info)
        return None

