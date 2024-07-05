from DevOri.client_mqtt import *
import asyncio
from DevOri.utils import dict2bytes
import os
from aiomqtt import Message
from DevOri.Aiomqtt_imp import make_FundementalClient
PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883


async def main():
    async with make_FundementalClient(host=HOST,
                                 port=PORT,
                                 prefix=PREFIX,
                                 verbose=True) as fc:
        
        friendly_name = "0x0c4314fffe19426b"
        sub = Subscriber[Message]()
        await fc.sub_topic(friendly_name, sub)
        while True:
            await fc.publish(f"{friendly_name}/get", dict2bytes({"battery": ""}))
            message = await sub.get_item()
            print(f"found {message.payload} at {message.topic}")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    
