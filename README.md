Volkswagen Carnet - An home assistant plugin to add integration with your car
============================================================
[![buy me a coffee](https://img.shields.io/badge/If%20you%20like%20it-Buy%20us%20a%20coffee-orange.svg?style=for-the-badge)](https://www.buymeacoffee.com/robinostlund)

Description
------------
This platform plugin allows you to see some information from volkswagen carnet related to your car that has a valid carnet subscription.

It also allows you to trigger some functions like start climatisation if your car supports that.

Remote engine heating is supported for combustion engine vehicles that uses the carnet portal together provided S-PIN. Probably not availabel for all car models.

Note: Some features included in the Passat GTE Facelift/MY2019> models are not yet implemented.

Installation
------------

Make sure you have a account on volkswagen carnet.

Clone or copy the root of the repository into `<config dir>/custom_components`

Add a volkswagencarnet configuration block to your `<config dir>/configuration.yaml`
```yaml
volkswagencarnet:
    username: <username to volkswagen carnet>
    password: <password to volkswagen carnet>
    spin: <S-PIN to volkswagen carnet>  
    scan_interval: 
        minutes: 2
    name:
        wvw1234567812356: 'Passat GTE'
    resources:
        - combustion_engine_heating # Note that this option is only available for 2019> Facelift model
        - position
        - distance
        - service_inspection
        - oil_inspection
        - door_locked
        - trunk_locked
        - request_in_progress
```

* **spin:** (optional) required for supporting combustion engine heating start/stop.

* **scan_interval:** (optional) specify in minutes how often to fetch status data from carnet. (default 5 min, minimum 1 min)

* **name:** (optional) set a friendly name of your car you can use the name setting as in confiugration example.

* **resources:** (optional) list of resources that should be enabled. (by default all resources is enabled).

Available resources:
```
    'position',
    'distance',
    'electric_climatisation',
    'combustion_climatisation',
    'window_heater',
    'combustion_engine_heating',
    'charging',
    'adblue_level',
    'battery_level',
    'fuel_level',
    'service_inspection',
    'oil_inspection',
    'last_connected',
    'charging_time_left',
    'electric_range',
    'combustion_range',
    'combined_range',
    'charge_max_ampere',
    'climatisation_target_temperature',
    'external_power',
    'parking_light',
    'climatisation_without_external_power',
    'door_locked',
    'trunk_locked',
    'request_in_progress'
```

Example of entities
------------
![alt text](https://user-images.githubusercontent.com/12171819/55963464-30216480-5c73-11e9-9b91-3bf06672ef36.png)



Automation example
------------
In this example we are sending notifications to a slack channel

`<config dir>/automations.yaml`
```yaml
# Get notifications when climatisation is started/stopped
- alias: vw_carid_climatisation_on
  trigger:
   platform: state
   entity_id: switch.vw_carid_climatisation
   from: 'off'
   to: 'on'
  action:
   service: notify.slack
   data_template:
    title: "VW climatisation started"
    message: "VW climatisation started"

- alias: vw_carid_climatisation_off
  trigger:
   platform: state
   entity_id: switch.vw_carid_climatisation
   from: 'on'
   to: 'off'
  action:
   service: notify.slack
   data_template:
    title: "VW climatisation stopped"
    message: "VW climatisation stopped"
    
# Get notifications when vehicle is charging
- alias: vw_carid_charging
  trigger:
   platform: state
   entity_id: switch.vw_carid_charging
   from: 'off'
   to: 'on'
  action:
   service: notify.slack
   data_template:
    title: "VW is now charging"
    message: "VW is now charging"

# Get notifications when vehicle is fully charged
- alias: vw_carid_battery_fully_charged
  trigger:
   platform: numeric_state
   entity_id: switch.vw_carid_battery_level
   above: 99
  action:
   service: notify.slack
   data_template:
    title: "VW is now fully charged"
    message: "VW is now fully charged"
```

Enable debug logging
------------
```yaml
logger:
    default: info
    logs:
        custom_components.volkswagencarnet: debug
        custom_components.volkswagencarnet.climate: debug
        custom_components.volkswagencarnet.lock: debug
        custom_components.volkswagencarnet.device_tracker: debug
        custom_components.volkswagencarnet.switch: debug
        custom_components.volkswagencarnet.binary_sensor: debug
        custom_components.volkswagencarnet.sensor: debug
 ```

Lovelace Card
------------
Check out this awesome lovelace card by endor
https://github.com/endor-force/lovelace-carnet

![alt text](https://user-images.githubusercontent.com/12171819/55963632-7d9dd180-5c73-11e9-9eea-c2b211f6843b.png)
