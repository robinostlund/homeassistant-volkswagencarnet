[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

Volkswagen Carnet - An home assistant plugin to add integration with your car
=============================================================================

[![buy me a coffee](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/robinostlund)

Description
------------

This platform plugin allows you to see some information from volkswagen carnet related to your car that has a valid carnet subscription.

It also allows you to trigger some functions like start climatisation if your car supports that.

Remote engine heating is supported for combustion engine vehicles that use the carnet portal together with a provided S-PIN. Not available for all car models.

Note: Some features included in Volkswagen WeConnect 2019 and newer are not fully tested. This custom component should work with any models such as Golf/Passat 8.5/Tiguan etc. But please bear with me and report any fault or error as an issue.
The current release (2020-06-13) has been tested with a Passat GTE MY2017 and a Passat GTE MY2020 with full functionality.
Users report success with the e-Up! 2020.

Installation
------------

Make sure you have an account on volkswagen carnet.

Clone or copy the repository and copy the folder 'homeassistant-volkswagencarnet/custom_component/volkswagencarnet' into '<config dir>/custom_components'

Add a volkswagencarnet configuration block to your `<config dir>/configuration.yaml`:
```yaml
volkswagencarnet:
    username: <username for volkswagen carnet>
    password: <password for volkswagen carnet>
    spin: <S-PIN for volkswagen carnet>
    scandinavian_miles: false
    scan_interval:
        minutes: 2
    name:
        wvw1234567812356: 'Passat GTE'
    resources:
        - combustion_engine_heating # Note that this option is only available for 2019> Facelift models
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

* **scandinavian_miles:** (optional) specify true if you want to change from km to mil on sensors

* **name:** (optional) map the vehicle identification number (VIN) to a friendly name of your car. This name is then used for naming all entities. See the configuration example. (by default, the VIN is used)

* **resources:** (optional) list of resources that should be enabled. (by default, all resources are enabled)

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
    'request_in_progress',
    'windows_closed',
    'trip_last_average_speed',
    'trip_last_average_electric_consumption',
    'trip_last_average_fuel_consumption',
    'trip_last_duration'
```

Example of entities
-------------------

![alt text](https://user-images.githubusercontent.com/12171819/55963464-30216480-5c73-11e9-9b91-3bf06672ef36.png)

Automation example
------------------

In this example we are sending notifications to a slack channel

`<config dir>/automations.yaml`
```yaml
# Send notification when climatisation is started/stopped
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

# Send notification when vehicle is charging
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

# Send notification when vehicle is fully charged
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

# Announce that the car is unlocked but home
- id: 'car_is_unlocked'
  alias: The car is at home and unlocked
  trigger:
  - entity_id: binary_sensor.my_passat_gte_external_power
    platform: state
    to: 'on'
    for: 00:10:00
  condition:
  - condition: state
    entity_id: lock.my_passat_gte_door_locked
    state: unlocked
  - condition: state
    entity_id: device_tracker.life360_my_lord
    state: home
  - condition: time
    after: '07:00:00'
    before: '21:00:00'
  action:
# Notification via push message to smartphone
  - data:
      message: "The car is unlocked!"
      target:
      - device/my_device
    service: notify.device
# Notification via smart speaker (kitchen)
  - data:
      entity_id: media_player.kitchen
      volume_level: '0.6'
    service: media_player.volume_set
  - data:
      entity_id: media_player.kitchen
      message: "My Lord, the car is unlocked. Please attend this this issue at your earliest inconvenience!"
    service: tts.google_translate_say
```

Enable debug logging
--------------------

```yaml
logger:
    default: info
    logs:
        volkswagencarnet: debug
        custom_components.volkswagencarnet: debug
        custom_components.volkswagencarnet.climate: debug
        custom_components.volkswagencarnet.lock: debug
        custom_components.volkswagencarnet.device_tracker: debug
        custom_components.volkswagencarnet.switch: debug
        custom_components.volkswagencarnet.binary_sensor: debug
        custom_components.volkswagencarnet.sensor: debug
 ```

Lovelace Card
-------------

Check out this awesome lovelace card by endor
https://github.com/endor-force/lovelace-carnet

![alt text](https://user-images.githubusercontent.com/12171819/55963632-7d9dd180-5c73-11e9-9eea-c2b211f6843b.png)
