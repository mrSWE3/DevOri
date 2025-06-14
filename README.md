# DevOri

Communication over MQTT with the publish and subscribe model can be messy and unintuitive. 
By instead orienting communication with the device at the center, DevOrdi addresses both issues. 

All devices have topics under which they communicate, while a message broker facilitates the communication. Therefore, this python library standardizes and decouples devices and message brokers into a framework to promote IoT applications' reusability and extendability. Furthermore, the message broker is only a mean through which devices communicate. This fact is reflected by a device being a composite of a message broker and its valid topics. As a result, a device is free communicate as it wishes confined only by its valid topics. 

This intuitive abstraction is built on top of another made from treating the message broker as a observable. Instead of directly requesting information form a topic, observers subscribed to the topic will be notified with its content. This fundamental approach can be used on its own, although without any abstraction of devices. 

## Features
    - Fully async
    - Automatic topic unsubscription when devices are garbage collected
    - Payloads can be categorized and retrieved by contents 
    - Strictly typed, and documented

## Future work
    - Test and improve wildcard functionality
    - Simplify handling of categorized payloads

## Implementations
Correctly, DevOri has successfully been used for a personal [IoT project](https://github.com/Datavetenskapsdivisionen/monaden-iot).

