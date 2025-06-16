import asyncio
import time
import datetime
from aiomqtt import Client

async def clock_tick_sender(client: Client):
    while True:
        await asyncio.sleep(1)
        await client.publish("/clock", '""'.encode())  # Publish tick event on empty topic
        print("Tick sent at", datetime.datetime.now())

async def respond_to_time_requests(client: Client):
    await client.subscribe("/clock/get")  # Subscribe to time request topic
    async for message in client.messages:
        print(message.topic.value, message.payload)
        if message.topic.value == "/clock/get" and message.payload == b"current_time":
            timestamp = time.time()
            await client.publish("/clock", str(timestamp).encode())  # Publish current time response
            print(f"Responded with time: {timestamp}")



from amqtt.broker import Broker

config = {
    'listeners': {
        'default': {
            'type': 'tcp',
            'bind': '127.0.0.1:1883',
        },
    },
    'sys_interval': 10,
    'topic-check': {
        'enabled': False
    }
}




async def main():
    broker = Broker(config)
    await broker.start()
    async with Client("127.0.0.1", 1883) as client:
        await asyncio.gather(
            clock_tick_sender(client),
            respond_to_time_requests(client)
        )
  
if __name__ == "__main__":
    asyncio.run(main())
