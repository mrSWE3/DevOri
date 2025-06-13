
import os, sys
import asyncio
from  aiomqtt import Message as Message_ai
from aiomqtt.types import PayloadType
from typing import Literal, Any
from enum import Enum, auto


sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))


from DevOri.MqttDevices import Device
from DevOri.utils import any2bytes, bytes2any
from DevOri.Aiomqtt_imp import make_deviceClient


PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883


class RemoteCategory(Enum):
    BATTERYUPDATE = auto()
    ACTION = auto()

def sort_remote_payload(message: Message_ai) -> RemoteCategory:
    b: PayloadType = message.payload
    assert(isinstance(b, bytes))
    d: dict[str,Any] = bytes2any(b)
    assert(isinstance(d, dict))
    
    if "action" in d.keys():
        return RemoteCategory.ACTION
    else:
        return RemoteCategory.BATTERYUPDATE
async def main():
    
    async with make_deviceClient(host=HOST,
                                 port=PORT,
                                     prefix=PREFIX,
                                 verbose=False) as client:
        friendly_name = "0x0c4314fffe19426b"
        async with Device[bytes,Literal["get"], Message_ai, Literal[""], RemoteCategory](
                            friendly_name=friendly_name, 
                            communicator=client,
                            category_sorters={"": sort_remote_payload},
                            categories=RemoteCategory
                            ) as device:
            
            
                await device.send_to(topic="get",
                            payload=any2bytes({"battery": ""}))
                
                
                message = await device.receive_from(topic="", 
                                                   category=RemoteCategory.ACTION)
                print(f"found {message.payload} at {message.topic}")

if __name__ == "__main__":
    asyncio.run(main())
    
