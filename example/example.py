import asyncio
from DevOri.mqttDevices import Device
from DevOri.utils import dict2bytes
import os
from DevOri.Aiomqtt_imp import make_deviceClient
from aiomqtt import Message

PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883


async def main():
    
    async with make_deviceClient(host=HOST,
                                 port=PORT,
                                 prefix=PREFIX,
                                 verbose=True) as clinet:
        friendly_name = "0x0c4314fffe19426b"
        async with Device[bytes, Message](
                            friendly_name=friendly_name, 
                            communicator=clinet,
                            read_topics={""}
                            ) as device:
            
            while True:
                await device.send_to(topic="get",
                            payload=dict2bytes({"battery": ""}))
                
                
                message = await device.recive_from(topic="")
                print(f"found {message} at {message}")

if __name__ == "__main__":
    asyncio.run(main())
    
