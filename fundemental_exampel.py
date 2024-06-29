from client_mqtt import *
import asyncio
import json
from mqttDevices import DualDevice
from utils import dict2bytes
import os
PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
PORT = 1883

#Recomended to make factory methods for client construction
def make_FundementalClient(host: str, port: int, prefix: str, verbose: bool) -> FundementalClient:
    return FundementalClient(AiomqttPhysicalClient(
        AiomqttClient(hostname=host, port=port)),
        topic_prefix=prefix,
        verbose=verbose
        )
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
            print(message.payload)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    
