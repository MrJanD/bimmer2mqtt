#!/usr/bin/python3

import logging
import json
import time
import sys
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import logging
import requests

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name, valid_regions
from bimmer_connected.vehicle import VehicleViewDirection

TOPIC = "Mobility/MiniCooperSE/"

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class MQTT_Handler(object):
    def __init__(self):
        self.mqtt_server = "YOUR_IP"
        self.mqtt_port = 1883
        self.mqtt_sub_remote_service = TOPIC + "cmd"
        self.mqtt_sub_get_status = TOPIC + "get"
        self.mqtt_pub_properties = TOPIC + "properties"
        self.mqtt_pub_vehicleState = TOPIC + "vehicleState"
        self.mqtt_pub_executionState = TOPIC + "executionState"
        self.mqtt_pub_serviceState = "Mobility/service/state"
        self.client = mqtt.Client()

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Connected with result code "+str(rc))
        client.subscribe(self.mqtt_sub_get_status)
        client.message_callback_add(self.mqtt_sub_get_status, self.car_get_status)
        client.subscribe(self.mqtt_sub_remote_service)
        client.message_callback_add(self.mqtt_sub_remote_service, self.car_execute)
        client.publish(self.mqtt_pub_serviceState, "Online", retain = True)

    def on_disconnect(self, client, userdata, rc):
        logging.info("Disconnected with result code "+str(rc))
        client.publish(self.mqtt_pub_serviceState, "Offline", retain = True)

    def car_execute(self, client, userdata, message):
        logging.info("car_execute: " + message.topic + " " + str(message.payload))
        payload = str(message.payload).strip('\'').split()
        sw = ServiceWrapper(payload[0], payload[1], payload[2], payload[3], payload[4])
        token = MQTTClient_deliveryToken()
        sw.runCmd()
        client.publish(self.mqtt_pub_executionState, "DELIVERED")

    def car_get_status(self, client, userdata, message):
        logging.info("car_get_status: " + message.topic + " " + str(message.payload))
        payload = str(message.payload).strip('\'').split()
        sw = ServiceWrapper(payload[0], payload[1], payload[2], payload[3], payload[4])
        vehicleData = sw.get_status()
        client.publish(self.mqtt_pub_executionState, "DELIVERED")
        client.publish(self.mqtt_pub_properties, vehicleData['properties'])
        client.publish(self.mqtt_pub_vehicleState, vehicleData['status'])

    def run(self):
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.will_set(self.mqtt_pub_serviceState, "Offline", retain = True)
        self.client.connect(self.mqtt_server, self.mqtt_port, 60)
        self.client.loop_forever()

class ServiceWrapper(object):
    def __init__(self, cmd, username, password, region, vin):
        self.Cmd = cmd
        self.User = username
        self.Password = password
        self.Region = region
        self.VIN = vin

    def runCmd(self):
        if self.Cmd.lower() == 'state' or self.Cmd == 'status':
            return self.get_status()
        elif 'light' in self.Cmd.lower():
            return self.light_flash()
        elif 'unlock' in self.Cmd.lower():
            return self.unlock_doors()
        elif 'lock' in self.Cmd.lower():
            return self.lock_doors()
        elif 'air' in self.Cmd.lower():
            return self.air_conditioning()
        elif 'horn' in self.Cmd.lower():
            return self.blow_horn()
        else:
            return 'invalid command'

    def get_status(self) -> None:
        """Get the vehicle status."""
        account = ConnectedDriveAccount(self.User, self.Password, get_region_from_name(self.Region))
        account.update_vehicle_states()
        vData = dict()
        for vehicle in account.vehicles:
            if self.VIN == vehicle.vin:
                vData['properties'] = json.dumps(vehicle.attributes, indent=4)
                vData['status'] = json.dumps(vehicle.state.vehicle_status.attributes, indent=4)
        return vData

    def light_flash(self) -> None:
        """Trigger the vehicle to flash its lights."""
        account = ConnectedDriveAccount(self.User, self.Password, get_region_from_name(self.Region))
        vehicle = account.get_vehicle(self.VIN)
        if not vehicle:
            valid_vins = ", ".join(v.vin for v in account.vehicles)
            logging.info('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
            return
        status = vehicle.remote_services.trigger_remote_light_flash()
        return status.state

    def lock_doors(self) -> None:
        """Trigger the vehicle to lock its doors."""
        account = ConnectedDriveAccount(self.User, self.Password, get_region_from_name(self.Region))
        vehicle = account.get_vehicle(self.VIN)
        if not vehicle:
            valid_vins = ", ".join(v.vin for v in account.vehicles)
            logging.info('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
            return
        status = vehicle.remote_services.trigger_remote_door_lock()
        return status.state

    def unlock_doors(self) -> None:
        """Trigger the vehicle to unlock its doors."""
        account = ConnectedDriveAccount(self.User, self.Password, get_region_from_name(self.Region))
        vehicle = account.get_vehicle(self.VIN)
        if not vehicle:
            valid_vins = ", ".join(v.vin for v in account.vehicles)
            logging.info('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
            return
        status = vehicle.remote_services.trigger_remote_door_unlock()
        return status.state

    def air_conditioning(self) -> None:
        """Trigger the vehicle to enable air conditioning"""
        account = ConnectedDriveAccount(self.User, self.Password, get_region_from_name(self.Region))
        vehicle = account.get_vehicle(self.VIN)
        if not vehicle:
            valid_vins = ", ".join(v.vin for v in account.vehicles)
            logging.info('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
            return
        status = vehicle.remote_services.trigger_remote_air_conditioning()
        return status.state

    def blow_horn(self) -> None:
        """Trigger the vehicle to blow its horn"""
        account = ConnectedDriveAccount(self.User, self.Password, get_region_from_name(self.Region))
        vehicle = account.get_vehicle(self.VIN)
        if not vehicle:
            valid_vins = ", ".join(v.vin for v in account.vehicles)
            logging.info('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
            return
        status = vehicle.remote_services.trigger_remote_horn()
        return status.state


mqtt_handler = MQTT_Handler()
mqtt_handler.run()
