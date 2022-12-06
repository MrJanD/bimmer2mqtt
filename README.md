# bimmer2mqtt
For BMW and Mini drivers, who want to integrate their vehicle in almost any smart home solution.

Mapps https://github.com/bimmerconnected/bimmer_connected states, messages and commands to MQTT and vice versa. It comes along within an optinal dockerized environment, translation of geographic coordinates to human readable addresses and more.

USAGE:
- Replace the variables TOPIC, MQTT_SERVER, MQTT_PORT and REGION
- If your MQTT broker requires credentials: Uncomment self.client.username_pw_set(username="USERNAME", password="PASSWORD") and replace the user name and password
- Run the script as a service or in docker
- Publish a MQTT message to 
> Mobility/CarName/cmd

with payload 
> COMMAND USERNAME PASSWORD VIN

- _COMMAND_ can either be state, light, lock, unlock, air, horn or charge. 
- _USERNAME_ is your user name or mail address given in the connected drive portal.
- _PASSWORD_ is your password for the connected drive portal.
- _VIN_ is your vehicle identification number

Message Queuing Telemetry Transport (MQTT) is an open network communication protocol for Machine-to-Machine-Communication (M2M). It also acts as an widely accepted protocol for smart home systems and is therefore supported by many home automation servers.
Bimmer_connected is a simple library for BMW and MINI ConnectedDrive compatible cars. For a detailed description of the capabilities this library offers, see https://github.com/bimmerconnected/bimmer_connected. Moreover, the capabilities depend on your manufacturer, vehicle and allowed car controls. 

- Update 22.2: New JSON readings according to the connected drive latest changes
- Update 22.12: Compatibility with bimmer_connected 0.10.4

