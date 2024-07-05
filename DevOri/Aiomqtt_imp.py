from typing import AsyncGenerator, Any
from aiomqtt import Client as AiomqttClient, Message as Aiomessage
from client_mqtt import PhysicalClient, Message, DeviceClient, FundementalClient

class AiomqttPhysicalClient(PhysicalClient[bytes, Aiomessage]):
    def __init__(self, aiomqttClient: AiomqttClient) -> None:
        self._aiomqttClient = aiomqttClient
    async def subscribe(self, topic: str):
        await self._aiomqttClient.subscribe(topic)
    async def unsubscribe(self, topic: str):
        await self._aiomqttClient.unsubscribe(topic)
    async def publish(self, topic: str, payload: bytes):
        await self._aiomqttClient.publish(topic, payload)

    def get_receive_message_generator(self) -> AsyncGenerator[Message[Aiomessage], None]:
        class AG_wrapper(AsyncGenerator[Message[Aiomessage], None]):
            def __init__(self, c: AiomqttPhysicalClient) -> None:
                self.c = c
            def __aiter__(self):
                return self
            async def __anext__(self) -> Message[Aiomessage]:
                m = await self.c._aiomqttClient.messages.__anext__()
                return Message(m.topic.value, m)
        return AG_wrapper(self)
            
    async def __aenter__(self):
        await self._aiomqttClient.__aenter__()
        return self
    async def __aexit__(self,*exc_info: Any):
        await self._aiomqttClient.__aexit__(*exc_info)
        return None

def make_deviceClient(host: str, port: int, prefix: str, verbose: bool) -> DeviceClient[bytes, Aiomessage]:
    return  DeviceClient[bytes, Aiomessage](
                FundementalClient[bytes, Aiomessage]( 
                    AiomqttPhysicalClient(
                        AiomqttClient(hostname=host, port=port)), 
                                                    topic_prefix=prefix,
                                                    verbose=verbose))


def make_FundementalClient(host: str, port: int, prefix: str, verbose: bool) -> FundementalClient[bytes, Aiomessage]:
    return FundementalClient(AiomqttPhysicalClient(
        AiomqttClient(hostname=host, port=port)),
        topic_prefix=prefix,
        verbose=verbose
        )