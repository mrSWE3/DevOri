from client_mqtt import DeviceClient, FundementalClient, AiomqttClient, AiomqttPhysicalClient
import asyncio
from mqttDevices import DualDevice
from utils import dict2bytes
import os
from aiomqtt import Client as AiomqttClient, Message

PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883

#Recomended to make factory methods for client construction
def make_deviceClient(host: str, port: int, prefix: str, verbose: bool) -> DeviceClient[bytes, AioMessage]:
    return  DeviceClient[bytes, Message](
                FundementalClient[bytes, Message]( 
                    AiomqttPhysicalClient(
                        AiomqttClient(hostname=host, port=port)), 
                                                    topic_prefix=prefix,
                                                    verbose=verbose))
 
async def main():
    
    async with make_deviceClient(host=HOST,
                                 port=PORT,
                                 prefix=PREFIX,
                                 verbose=True) as clinet:
        friendly_name = "0x0c4314fffe19426b"
        async with DualDevice[bytes, Message](
                            friendly_name=friendly_name, 
                            communicator=clinet,
                            read_topics={""}
                            ) as device:
            while True:
                await device.send_to(topic="get",
                            payload=dict2bytes({"battery": ""}))
                
                
                message = await device.recive_from(topic="")
                print(f"found {message.payload} at {message.topic}")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    