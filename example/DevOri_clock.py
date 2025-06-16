import asyncio
import os, sys
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))
from DevOri.MqttDevices import Device, Communicator
from DevOri.Aiomqtt_imp import Aiomessage, make_deviceClient
from DevOri.utils import bytes2any
from typing import Literal, Callable
import datetime
from enum import Enum, auto


class ClockCategory(Enum):
    CURRENT_TIME = auto()
    TICK = auto()


async def tick_tock(clock: Device[bytes, Literal["get"], Aiomessage, Literal[""], ClockCategory]):
    old_time = datetime.datetime.now()
    while True:
        await clock.receive_from(topic="", category=ClockCategory.TICK)
        new_time = datetime.datetime.now()
        print(f"Tick at {new_time}, took {new_time - old_time}")
        old_time = new_time
        await asyncio.sleep(3) # Simulate some busy work

async def get_current_time(clock: Device[bytes, Literal["get"], Aiomessage, Literal[""], ClockCategory]):
    while True:
        await asyncio.to_thread(input, "Press Enter to get the current time... \n")
        await clock.send_to(topic="get", payload=b"current_time")
        message = await clock.receive_from(topic="", category=ClockCategory.CURRENT_TIME)
        assert(isinstance(message.payload, bytes)), "Expected bytes type"
        current_time = bytes2any(message.payload)
        print(f"Current time is {current_time}")


def make_DeviceClock[send_T, receive_T](client: Communicator[send_T, receive_T],
                                        clock_category_sorter: Callable[[receive_T], ClockCategory],
               ) -> Device[send_T, Literal["get"], receive_T, Literal[""], ClockCategory]:
    return Device[send_T, Literal["get"], receive_T, Literal[""], ClockCategory](
        friendly_name="clock",
        communicator=client,
        category_sorters={
            "": clock_category_sorter},
        categories=ClockCategory,
        message_save_limit={
            "": {ClockCategory.TICK: 1}
        },
        prefix=""
    ) 

def clock_category_sorter(message: Aiomessage) -> ClockCategory:
    assert isinstance(message.payload, bytes), "Expected bytes type"
    payload = bytes2any(message.payload)
    if isinstance(payload, float):
        return ClockCategory.CURRENT_TIME
    return ClockCategory.TICK

async def main():
    async with make_deviceClient(host="localhost",
                                 port=1883,
                                 prefix="",
                                 verbose=False) as client:
        
        async with make_DeviceClock(client, clock_category_sorter) as clock:
            await asyncio.gather(get_current_time(clock), tick_tock(clock))

if __name__ == "__main__":
    asyncio.run(main())
