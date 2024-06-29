from client_mqtt import *
import asyncio
import json
from mqttDevices import DualDevice
from utils import dict2bytes
import os
from aiomqtt import Client as AiomqttClient
PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883

#Recomended to make factory methods for client construction
def make_deviceClient(host: str, port: int, prefix: str, verbose: bool) -> DeviceClient:
    return DeviceClient(FundementalClient(AiomqttPhysicalClient(
        AiomqttClient(hostname=HOST, port=PORT)),
        topic_prefix=prefix,
        verbose=verbose
        ))
 
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
                print("found", message.payload)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    
