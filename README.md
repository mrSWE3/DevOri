# DevOri

Communication over MQTT with the publish and subscribe model can be messy and unintuitive. 
By instead orienting communication with the device at the center, DevOri addresses both issues. 

All devices have topics under which they communicate, while a message broker facilitates the communication. Therefore, this Python library standardizes and decouples devices and message brokers into a framework to promote IoT applications' reusability and extendability. Furthermore, the message broker is only a means through which devices communicate. This fact is reflected by a device being a composite of a message broker and its valid topics. As a result, a device is free to communicate as it wishes, confined only by its valid topics. 

This intuitive abstraction is built on top of another made from treating the message broker as an observable. Instead of directly requesting information from a topic, observers subscribed to the topic will be notified of its content. This fundamental approach can be used on its own, although without any abstraction of devices. 

## Features
    - Fully async
    - Automatic topic unsubscription when devices are garbage collected
    - Payloads can be categorized and retrieved by content 
    - Strictly typed and documented

## Example
To run the example code, you need to clone the repo found in [here](example/example_requirements.txt) (pip install -r example/example_requirements.txt). 
1. Run **python3 example/dummy_communication.py** 
This will start a message broker and a dummy clock. This clock is supposed to mimic how a real device might communicate. Every 10 seconds, it sends a tick to its base topic. Furthermore, it will also send the current time to the base topic if requested at "get."

2. Run **python3 example/DevOri_clock.py**, in another terminal
This script is an example of how DevOri can be used in an extendable and reusable way, all while being strictly typed. To begin with, it would  be beneficial to separate the tick notifications from the requested current time. Therefore, the messages are sorted under the *ClockCategory* enum with the *clock_category_sorter* method. By doing so, the different kinds of messages can be independently received in their corresponding server methods, *tick_tock* and *get_current_time*. 

The task of changing the library that handles client connections with the broker is simple. The only code that needs to be changed is the sorting method and client itself; the rest of the script can be reused as is. Adapting the sorting method to a new client library could be more structured, but it is left to future work. 


## Future work
    - Test and improve wildcard functionality
    - Simplify handling of categorized payloads 

## Implementations
Correctly, DevOri has successfully been used for a personal [IoT project](https://github.com/Datavetenskapsdivisionen/monaden-iot).

