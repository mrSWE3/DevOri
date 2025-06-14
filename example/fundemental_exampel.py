import os
import sys
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))

from DevOri.Clients import *
import asyncio
from DevOri.utils import any2bytes, QueueSubscriber

from aiomqtt import Message as Message_Aio
from DevOri.Aiomqtt_imp import make_FundamentalClient
PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883


async def main():
    async with make_FundamentalClient(host=HOST,
                                 port=PORT,
                                 prefix=PREFIX,
                                 verbose=True) as fc:
        
        friendly_name = "0x0c4314fffe19426b"
        sub = QueueSubscriber[Message_Aio]()
        await fc.sub_topic(friendly_name, sub)
        while True:
            await fc.publish(f"{friendly_name}/get", any2bytes({"battery": ""}))
            message = await sub.get_item()
        
            print(f"found {message.payload} at {message.topic}")

if __name__ == "__main__":
    asyncio.run(main())
    
