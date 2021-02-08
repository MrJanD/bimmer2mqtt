#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import logging
import json
import time
import sys
import threading
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import logging

from pathlib import Path

import requests

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name, valid_regions
from bimmer_connected.vehicle import VehicleViewDirection

TEXT_VIN = 'Vehicle Identification Number'
TOPIC = "Mobility/MiniCooperSE/"

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class MQTT_Handler(object):
    def __init__(self):
        self.mqtt_server = "192.168.0.11"
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










#def main_parser() -> argparse.ArgumentParser:
#    """Creates the ArgumentParser with all relevant subparsers."""
#    logging.basicConfig(level=logging.DEBUG)

#    parser = argparse.ArgumentParser(description='A simple executable to use and test the library.')
#    subparsers = parser.add_subparsers(dest='cmd')
#    subparsers.required = True

#    status_parser = subparsers.add_parser('status', description='Get the current status of the vehicle.')
#    _add_default_arguments(status_parser)
#    _add_position_arguments(status_parser)

#    fingerprint_parser = subparsers.add_parser('fingerprint', description='Save a vehicle fingerprint.')
#    _add_default_arguments(fingerprint_parser)
#    _add_position_arguments(fingerprint_parser)
#    fingerprint_parser.set_defaults(func=fingerprint)

#    flash_parser = subparsers.add_parser('lightflash', description='Flash the vehicle lights.')
#    _add_default_arguments(flash_parser)
#    flash_parser.add_argument('vin', help=TEXT_VIN)
#    flash_parser.set_defaults(func=light_flash)

#    finder_parser = subparsers.add_parser('vehiclefinder', description='Update the vehicle GPS location.')
#    _add_default_arguments(finder_parser)
#    finder_parser.add_argument('vin', help=TEXT_VIN)
#    finder_parser.set_defaults(func=vehicle_finder)

#    image_parser = subparsers.add_parser('image', description='Download a vehicle image.')
#    _add_default_arguments(image_parser)
#    image_parser.add_argument('vin', help=TEXT_VIN)
#    image_parser.set_defaults(func=image)

#    sendpoi_parser = subparsers.add_parser('sendpoi', description='Send a point of interest to the vehicle.')
#    _add_default_arguments(sendpoi_parser)
#    sendpoi_parser.add_argument('vin', help=TEXT_VIN)
#    sendpoi_parser.add_argument('latitude', help='Latitude of the POI', type=float)
#    sendpoi_parser.add_argument('longitude', help='Longitude of the POI', type=float)
#    sendpoi_parser.add_argument('--name', help='(optional, display only) Name of the POI', nargs='?', default=None)
#    sendpoi_parser.add_argument('--street', help='(optional, display only) Street & House No. of the POI',
#                                nargs='?', default=None)
#    sendpoi_parser.add_argument('--city', help='(optional, display only) City of the POI', nargs='?', default=None)
#    sendpoi_parser.add_argument('--postalcode', help='(optional, display only) Postal code of the POI',
#                                nargs='?', default=None)
#    sendpoi_parser.add_argument('--country', help='(optional, display only) Country of the POI',
#                                nargs='?', default=None)
#    sendpoi_parser.set_defaults(func=send_poi)

#    sendpoi_from_address_parser = subparsers.add_parser('sendpoi_from_address',
#                                                        description=('Send a point of interest parsed from a'
#                                                                     ' street address to the vehicle.'))
#    _add_default_arguments(sendpoi_from_address_parser)
#    sendpoi_from_address_parser.add_argument('vin', help=TEXT_VIN)
#    sendpoi_from_address_parser.add_argument('-n', '--name', help='(optional, display only) Name of the POI',
#                                             nargs='?', default=None)
#    sendpoi_from_address_parser.add_argument('-a', '--address', nargs='+',
#                                             help="Address (e.g. 'Street 17, city, zip, country')")
#    sendpoi_from_address_parser.set_defaults(func=send_poi_from_address)

#    message_parser = subparsers.add_parser('sendmessage', description='Send a text message to the vehicle.')
#    _add_default_arguments(message_parser)
#    message_parser.add_argument('vin', help=TEXT_VIN)
#    message_parser.add_argument('text', help='Text to be sent.')
#    message_parser.add_argument('subject', help='(optional) Message subject', nargs='?')
#    message_parser.set_defaults(func=send_message)

#    return parser


#def get_status(args) -> None:
#    """Get the vehicle status."""
#    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
#    if args.lat and args.lng:
#        for vehicle in account.vehicles:
#            vehicle.set_observer_position(args.lat, args.lng)
#    account.update_vehicle_states()

#    for vehicle in account.vehicles:
#        print('VIN: {}'.format(vehicle.vin))
#        print('Mileage: {}'.format(vehicle.state.vehicle_status.mileage))
#        print('Vehicle properties:')
#        print(json.dumps(vehicle.attributes, indent=4))
#        print('Vehicle status:')
#        print(json.dumps(vehicle.state.vehicle_status.attributes, indent=4))

#def get_status(username, password, region, vin) -> None:
#    """Get the vehicle status."""
#    account = ConnectedDriveAccount(username, password, get_region_from_name(region))
#    account.update_vehicle_states()
#    vData = dict()
#    for vehicle in account.vehicles:
#        if vin == vehicle.vin:
#            vData['mileage'] = vehicle.state.vehicle_status.mileage
#            vData['properties'] = json.dumps(vehicle.attributes, indent=4)
#            vData['status'] = json.dumps(vehicle.state.vehicle_status.attributes, indent=4)
#    return vData

#def light_flash(username, password, region, vin) -> None:
#    """Trigger the vehicle to flash its lights."""
#    account = ConnectedDriveAccount(username, password, get_region_from_name(region))
#    vehicle = account.get_vehicle(vin)
#    if not vehicle:
#        valid_vins = ", ".join(v.vin for v in account.vehicles)
#        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
#        return
#    status = vehicle.remote_services.trigger_remote_light_flash()
#    return status.state

#def vehicle_finder(args) -> None:
#    """Trigger the vehicle finder to locate it."""
#    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
#    vehicle = account.get_vehicle(args.vin)
#    if not vehicle:
#        valid_vins = ", ".join(v.vin for v in account.vehicles)
#        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
#        return
#    status = vehicle.remote_services.trigger_remote_vehicle_finder()
#    print(status.state)


#def image(args) -> None:
#    """Download a rendered image of the vehicle."""
#    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
#    vehicle = account.get_vehicle(args.vin)

#    with open('image.png', 'wb') as output_file:
#        image_data = vehicle.get_vehicle_image(400, 400, VehicleViewDirection.FRONT)
#        output_file.write(image_data)
#    print('vehicle image saved to image.png')


#def send_poi(args) -> None:
#    """Send Point Of Interest to car."""
#    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
#    vehicle = account.get_vehicle(args.vin)
#    poi_data = dict(
#        lat=args.latitude,
#        lon=args.longitude,
#        name=args.name,
#        street=args.street,
#        city=args.city,
#        postal_code=args.postalcode,
#        country=args.country
#    )
#    vehicle.remote_services.trigger_send_poi(poi_data)


#def send_poi_from_address(args) -> None:
#    """Create Point of Interest from OSM Nominatim and send to car."""
#    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
#    vehicle = account.get_vehicle(args.vin)
#    address = [(str(' '.join(args.address)))]
#    try:
#        response = requests.get("https://nominatim.openstreetmap.org",
#                                params={
#                                    "q": address,
#                                    "format": "json",
#                                    "addressdetails": 1,
#                                    "limit": 1
#                                }).json()[0]
#    except IndexError:
#        print('\nAddress not found')
#        sys.exit(1)
#    address = response.get("address", {})
#    city = address.get("city")
#    town = address.get("town")

#    poi_data = dict(
#        lat=response["lat"],
#        lon=response["lon"],
#        name=args.name,
#        street=address.get("road"),
#        city=town if city is None and town is not None else None,
#        postal_code=address.get("postcode"),
#        country=address.get("country")
#    )
#    vehicle.remote_services.trigger_send_poi(poi_data)


#def send_message(args) -> None:
#    """Send a message to car."""
#    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
#    vehicle = account.get_vehicle(args.vin)
#    msg_data = dict(
#        text=args.text,
#        subject=args.subject
#    )
#    vehicle.remote_services.trigger_send_message(msg_data)


#def _add_default_arguments(parser: argparse.ArgumentParser):
#    """Add the default arguments username, password, region to the parser."""
#    parser.add_argument('username', help='Connected Drive username')
#    parser.add_argument('password', help='Connected Drive password')
#    parser.add_argument('region', choices=valid_regions(), help='Region of the Connected Drive account')


#def _add_position_arguments(parser: argparse.ArgumentParser):
#    """Add the lat and lng attributes to the parser."""
#    parser.add_argument('lat', type=float, nargs='?', const=0.0,
#                        help='(optional) Your current GPS latitude (as float)')
#    parser.add_argument('lng', type=float, nargs='?', const=0.0,
#                        help='(optional) Your current GPS longitude (as float)')
#    parser.set_defaults(func=get_status)


#def main():
#    """Main function."""
#    parser = main_parser()
#    args = parser.parse_args()
#    args.func(args)


#if __name__ == '__main__':
#    main()

