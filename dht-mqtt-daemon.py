#!/usr/bin/python3

import socket
import ssl
import sys
import re
import json
import os.path
import argparse
from time import time, sleep, localtime, strftime
from colorama import init as colorama_init
from colorama import Fore, Back, Style
from configparser import ConfigParser
from unidecode import unidecode
import Adafruit_DHT as dht
import paho.mqtt.client as mqtt
import sdnotify

project_name = 'DHT Raspberry MQTT Client/Daemon'
project_url = 'https://github.com/R4scal/dht-mqtt-daemon'

if False:
    # will be caught by python 2.7 to be illegal syntax
    print('Sorry, this script requires a python3 runtime environemt.', file=sys.stderr)


# Argparse
parser = argparse.ArgumentParser(description=project_name, epilog='For further details see: ' + project_url)
parser.add_argument('--config_dir', help='set directory where config.ini is located', default=sys.path[0])
parse_args = parser.parse_args()

# Intro
colorama_init()
print(Fore.GREEN + Style.BRIGHT)
print(project_name)
print('Source:', project_url)
print(Style.RESET_ALL)

# Systemd Service Notifications - https://github.com/bb4242/sdnotify
sd_notifier = sdnotify.SystemdNotifier()

# Logging function
def print_line(text, error = False, warning=False, sd_notify=False, console=True):
    timestamp = strftime('%Y-%m-%d %H:%M:%S', localtime())
    if console:
        if error:
            print(Fore.RED + Style.BRIGHT + '[{}] '.format(timestamp) + Style.RESET_ALL + '{}'.format(text) + Style.RESET_ALL, file=sys.stderr)
        elif warning:
            print(Fore.YELLOW + '[{}] '.format(timestamp) + Style.RESET_ALL + '{}'.format(text) + Style.RESET_ALL)
        else:
            print(Fore.GREEN + '[{}] '.format(timestamp) + Style.RESET_ALL + '{}'.format(text) + Style.RESET_ALL)
    timestamp_sd = strftime('%b %d %H:%M:%S', localtime())
    if sd_notify:
        sd_notifier.notify('STATUS={} - {}.'.format(timestamp_sd, unidecode(text)))

# Eclipse Paho callbacks - http://www.eclipse.org/paho/clients/python/docs/#callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print_line('MQTT connection established', console=True, sd_notify=True)
        print()
    else:
        print_line('Connection error with result code {} - {}'.format(str(rc), mqtt.connack_string(rc)), error=True)
        #kill main thread
        os._exit(1)

def on_publish(client, userdata, mid):
    #print_line('Data successfully published.')
    pass


# Load configuration file
config_dir = parse_args.config_dir

config = ConfigParser(delimiters=('=', ))
config.optionxform = str
config.read([os.path.join(config_dir, 'config.ini.dist'), os.path.join(config_dir, 'config.ini')])

reporting_mode = config['General'].get('reporting_method', 'homeassistant-mqtt')
daemon_enabled = config['Daemon'].getboolean('enabled', True)
sleep_period = config['Daemon'].getint('period', 300)
pin = config['Sensor'].getint('pin', 4)

if reporting_mode == 'homeassistant-mqtt':
    default_base_topic = 'homeassistant'

base_topic = config['MQTT'].get('base_topic', default_base_topic).lower()

# Check configuration
if reporting_mode not in ['homeassistant-mqtt']:
    print_line('Configuration parameter reporting_mode set to an invalid value', error=True, sd_notify=True)
    sys.exit(1)

print_line('Configuration accepted', console=False, sd_notify=True)

# MQTT connection
if reporting_mode in ['homeassistant-mqtt']:
    print_line('Connecting to MQTT broker ...')
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish = on_publish

    if config['MQTT'].getboolean('tls', False):
        # According to the docs, setting PROTOCOL_SSLv23 "Selects the highest protocol version
        # that both the client and server support. Despite the name, this option can select
        # “TLS” protocols as well as “SSL”" - so this seems like a resonable default
        mqtt_client.tls_set(
            ca_certs=config['MQTT'].get('tls_ca_cert', None),
            keyfile=config['MQTT'].get('tls_keyfile', None),
            certfile=config['MQTT'].get('tls_certfile', None),
            tls_version=ssl.PROTOCOL_SSLv23
        )

    if config['MQTT'].get('username'):
        mqtt_client.username_pw_set(config['MQTT'].get('username'), config['MQTT'].get('password', None))
    try:
        mqtt_client.connect(config['MQTT'].get('hostname', 'localhost'),
                            port=config['MQTT'].getint('port', 1883),
                            keepalive=config['MQTT'].getint('keepalive', 60))
    except:
        print_line('MQTT connection error. Please check your settings in the configuration file "config.ini"', error=True, sd_notify=True)
        sys.exit(1)
    else:
       mqtt_client.loop_start()
       sleep(1.0) # some slack to establish the connection

sd_notifier.notify('READY=1')

# Initialize DHT sensor
sensor_name = '{}_dht'.format(socket.gethostname()).replace("-", "_")
print_line('Current sensor name is "{}"'.format(sensor_name).lower())
sensor = dht.DHT22

# Discovery Announcement
if reporting_mode == 'homeassistant-mqtt':
    print_line('Announcing DHT22 to MQTT broker for auto-discovery ...')
    topic_path = '{}/sensor/{}'.format(base_topic, sensor_name)
    base_payload = {
        "state_topic": "{}/state".format(topic_path).lower()
    }
    # Temperature
    payload = dict(base_payload.items())
    payload['unit_of_measurement'] = '°C'
    payload['value_template'] = "{{ value_json.temperature }}"
    payload['name'] = "{} Temperature".format(sensor_name)
    payload['device_class'] = 'temperature'
    mqtt_client.publish('{}/{}_temperature/config'.format(topic_path, sensor_name).lower(), json.dumps(payload), 1, True)
    # Humidity
    payload = dict(base_payload.items())
    payload['unit_of_measurement'] = '%'
    payload['value_template'] = "{{ value_json.humidity }}"
    payload['name'] = "{} Humidity".format(sensor_name)
    payload['device_class'] = 'humidity'
    mqtt_client.publish('{}/{}_humidity/config'.format(topic_path, sensor_name).lower(), json.dumps(payload), 1, True)

# Sensor data retrieval and publication
while True:
   print_line('Retrieving data from DHT sensor...')
   humidity, temperature = dht.read_retry(sensor, pin)
   if humidity is None and temperature is None:
      print_line('Unable to get data form sensor.', error=True, sd_notify=True)
      print()
      continue
   else:
     data = dict()
     data['humidity'] = '{0:0.1f}'.format(humidity)
     data['temperature'] = '{0:0.1f}'.format(temperature)
     print_line('Result: {}'.format(json.dumps(data)))
     if reporting_mode == 'homeassistant-mqtt':
          print_line('Publishing to MQTT topic "{}/sensor/{}/state"'.format(base_topic, sensor_name).lower())
          mqtt_client.publish('{}/sensor/{}/state'.format(base_topic, sensor_name).lower(), json.dumps(data))
          sleep(0.5) # some slack for the publish roundtrip and callback function
     else:
          raise NameError('Unexpected reporting_mode.')
     print()

     print_line('Status messages published', console=False, sd_notify=True)

   if daemon_enabled:
      print_line('Sleeping ({} seconds) ...'.format(sleep_period))
      sleep(sleep_period)
      print()
   else:
      print_line('Execution finished in non-daemon-mode', sd_notify=True)
      break
