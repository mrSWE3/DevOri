
import os, sys
import asyncio
from aiomqtt import Message as Message_ai
from typing import Literal
from enum import Enum, auto


sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))


from mqttDevices import Device
from utils import dict2bytes, bytes2dict
from Aiomqtt_imp import make_deviceClient


PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883


class RemoteCategory(Enum):
    BATTERYUPDATE = auto()
    ACTION = auto()

def sort_remote_payload(message: Message_ai) -> RemoteCategory:
    b: bytes = message.payload  # type: ignore
    payload = bytes2dict(b).keys() 
    
    if "action" in payload:
        return RemoteCategory.ACTION
    else:
        return RemoteCategory.BATTERYUPDATE
async def main():
    
    async with make_deviceClient(host=HOST,
                                 port=PORT,
                                 prefix=PREFIX,
                                 verbose=False) as clinet:
        friendly_name = "0x0c4314fffe19426b"
        async with Device[bytes,Literal["get"], Message_ai, Literal[""], RemoteCategory](
                            friendly_name=friendly_name, 
                            communicator=clinet,
                            category_sorters={"": sort_remote_payload},
                            categories=RemoteCategory
                            ) as device:
            
            while True:
                await device.send_to(topic="get",
                            payload=dict2bytes({"battery": ""}))
                
                
                message = await device.recive_from(topic="", 
                                                   category=RemoteCategory.ACTION)
                print(f"found {type(message)} at {message.topic}")

if __name__ == "__main__":
    asyncio.run(main())
    
