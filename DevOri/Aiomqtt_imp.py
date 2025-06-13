from typing import AsyncGenerator, Any
from aiomqtt import Client as AiomqttClient, Message as Aiomessage
from .Clients import PhysicalClient, Message, DeviceClient, FundamentalClient

class AiomqttPhysicalClient(PhysicalClient[bytes, Aiomessage]):
    """
    ## Summary
        A wrapper of a aiomqtt client to function as a PhysicalClient
    """
    def __init__(self, aiomqttClient: AiomqttClient) -> None:
        self._aiomqttClient = aiomqttClient

    async def subscribe(self, topic: str) -> None:
        await self._aiomqttClient.subscribe(topic)
    async def unsubscribe(self, topic: str):
        await self._aiomqttClient.unsubscribe(topic)
    async def publish(self, topic: str, payload: bytes):
        await self._aiomqttClient.publish(topic, payload)

    def get_receive_message_generator(self) -> AsyncGenerator[Message[Aiomessage], None]:
        async def f() -> AsyncGenerator[Message[Aiomessage], None]:
            async for message in self._aiomqttClient.messages:
                yield Message[Aiomessage](message.topic.value, message)
        return f() 
    
    async def __aenter__(self):
        await self._aiomqttClient.__aenter__()
        return self
    
    async def __aexit__(self,*exc_info: Any):
        await self._aiomqttClient.__aexit__(*exc_info)
        return None

def make_deviceClient(host: str, port: int, prefix: str, verbose: bool) -> DeviceClient[bytes, Aiomessage]:
    """
    ## Summary
        Factory method for creating a DeviceClient with aiomqtt
    ## Args
        host (str): address of the host
        port (int): the port of at the host address
        prefix (str): prefix to all topics
        verbose (bool): if true, prints internal operations 
    ## Return
        DeviceClient[bytes, Aiomessage]
    """
    return  DeviceClient[bytes, Aiomessage](
                FundamentalClient[bytes, Aiomessage]( 
                    AiomqttPhysicalClient(
                        AiomqttClient(hostname=host, port=port)), 
                                                    topic_prefix=prefix,
                                                    verbose=verbose))


def make_FundamentalClient(host: str, port: int, prefix: str, verbose: bool) -> FundamentalClient[bytes, Aiomessage]:
    """
    ## Summary
        Factory method for creating a FundamentalClient with aiomqtt
    ## Args
        host (str): address of the host
        port (int): the port of at the host address
        prefix (str): prefix to all topics
        verbose (bool): if true, prints internal operations 
    ## Return
        FundamentalClient[bytes, Aiomessage]
    """
    return FundamentalClient(AiomqttPhysicalClient(
        AiomqttClient(hostname=host, port=port)),
        topic_prefix=prefix,
        verbose=verbose
        )