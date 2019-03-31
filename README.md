# DHT Raspberry MQTT Client/Daemon

Linux service to collect and transfer DHT22/DHT11 sensor data via MQTT to Home Assistant
A simple Linux python script to query DHT22/DHT11 sensor on Raspberry Pi and send the data to an **MQTT** broker,
e.g., the famous [Eclipse Mosquitto](https://projects.eclipse.org/projects/technology.mosquitto).
After data made the hop to the MQTT broker it can be used by home automation software, like [Home Assistant](https://www.home-assistant.io/).

The program can be executed in **daemon mode** to run continuously in the background, e.g., as a systemd service.
## Features

* Tested with DHT22 sensors
* Build on top of [Adafruit Python DHT Sensor Library](https://github.com/adafruit/Adafruit_Python_DHT)
* Highly configurable
* Data publication via MQTT
* Configurable topic and payload:
    * using the [HomeAssistant MQTT discovery format](https://home-assistant.io/docs/mqtt/discovery/)
* Announcement messages to support auto-discovery services
* MQTT authentication support
* No special/root privileges needed
* Daemon mode (default)
* Systemd service, sd\_notify messages generated
* Tested on Raspberry Pi 3

### Readings

The DHT sensor offers the following readings:

| Name            | Description |
|-----------------|-------------|
| `temperature`   | Air temperature, in [°C] (0.1°C resolution) |
| `humidity`       | humidity level, in [%]  (0.1% resolution) |

## Prerequisites

An MQTT broker is needed as the counterpart for this daemon.
Even though an MQTT-less mode is provided, it is not recommended for normal smart home automation integration.
MQTT is huge help in connecting different parts of your smart home and setting up of a broker is quick and easy.

## Installation

On a modern Linux system just a few steps are needed to get the daemon working.
The following example shows the installation under Debian/Raspbian below the `/opt` directory:

```shell
sudo apt install git python3 python3-pip

git clone https://github.com/R4scal/dht-mqtt-daemon.git /opt/dht-mqtt-daemon

cd /opt/dht-mqtt-daemon
sudo pip3 install -r requirements.txt
```

## Configuration

To match personal needs, all operation details can be configured using the file [`config.ini`](config.ini.dist).
The file needs to be created first:

```shell
cp /opt/dht-mqtt-daemon/config.{ini.dist,ini}
vim /opt/dht-mqtt-daemon/config.ini
```

## Execution

A first test run is as easy as:

```shell
python3 /opt/dht-mqtt-daemon/dht-mqtt-daemon.py
```

Using the command line argument `--config`, a directory where to read the config.ini file from can be specified, e.g.

```shell
python3 /opt/dht-mqtt-daemon/dht-mqtt-daemon.py --config /opt/dht-config
```

The extensive output can be reduced to error messages:

```shell
python3 /opt/dht-mqtt-daemon/dht-mqtt-daemon.py > /dev/null
```
