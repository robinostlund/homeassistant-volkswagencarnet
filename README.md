[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
![Version](https://img.shields.io/github/v/release/robinostlund/homeassistant-volkswagencarnet)
![PyPi](https://img.shields.io/pypi/v/volkswagencarnet?label=latest%20pypi)
![Downloads](https://img.shields.io/github/downloads/robinostlund/homeassistant-volkswagencarnet/total)


# Volkswagen Carnet - An home assistant plugin to add integration with your car

[![buy me a coffee](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/robinostlund)

## Description

This platform plugin allows you to see some information from volkswagen carnet related to your car that has a valid carnet subscription.

It also allows you to trigger some functions like start climatisation if your car supports that.

Remote engine heating is supported for combustion engine vehicles that use the carnet portal together with a provided S-PIN. Not available for all car models.

Note: Some features included in Volkswagen WeConnect 2019 and newer are not fully tested. This custom component should work with any models such as Golf/Passat 8.5/Tiguan etc. But please bear with me and report any fault or error as an issue.
The current release (2020-06-13) has been tested with a Passat GTE MY2017 and a Passat GTE MY2020 with full functionality.
Users report success with the e-Up! 2020.

## Having issues with this custom component?
Please, before posting an issue make sure that VW´s WeConnect service works for you via a normal web browser. Not only the login part but also make sure that the VW WeConnect service interacts with the car proper, including updating of all sensors and location. If there are problems with the VW WeConnect service this component will not work either. This custom component is only as good as the VW WeConnect service.

## Installation

### Install with HACS (recomended)

Do you you have [HACS](https://community.home-assistant.io/t/custom-component-hacs) installed? Just search for Volkswagen We Connect and install it direct from HACS. HACS will keep track of updates and you can easly upgrade volkswagencarnet to latest version.

### Install manually
Make sure you have an account on volkswagen carnet.

Clone or copy the repository and copy the folder 'homeassistant-volkswagencarnet/custom_component/volkswagencarnet' into '<config dir>/custom_components'

## Configuration
Configure via UI: Configuration > Integrations

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
    'door_closed_left_front',
    'door_closed_right_front',
    'door_closed_left_back',
    'door_closed_right_back',
    'trunk_locked',
    'trunk_closed',
    'request_in_progress',
    'sunroof_closed',
    'windows_closed',
    'window_closed_left_front',
    'window_closed_right_front',
    'window_closed_left_back',
    'window_closed_right_back',
    'trip_last_average_speed',
    'trip_last_average_electric_consumption',
    'trip_last_average_fuel_consumption',
    'trip_last_duration'
```

## Entities

This plugin creates entities in the format `DOMAIN.NAME_ENTITY`. Not all entities are created for all cars, for example pure electric cars will not have entities only applicable to cars with a combustion engine.
* **device_tracker.NAME_position:** GPS coordinates of the place the car was parked.
* **sensor.NAME_odometer:** total distance the car has travelled.
* **climate.NAME_electric_climatisation:** climate control for the car. Turning it on will pre-heat or cool the car. BEVs only.
* **climate.NAME_combustion_climatisation:** climate control for the car. Turning it on will pre-heat or maybe cool the car. Only for cars with a cumbustion engine. May require optional equipment.
* **window_heater**
* **combustion_engine_heating**
* **switch.NAME_charging:** indicates and controls whether the car is charging. BEVs and PHEVs only.
* **sensor.NAME_adblue_level:** indicates how full the diesel exhaust fluid tank is. Cars with diesel engines only.
* **sensor.NAME_battery_level:** state of charge of the traction battery. BEVs and (P)HEVs only.
* **sensor.NAME_fuel_level:** indicates how full the fuel tank is. Cars with combustion engines only.
* **sensor.NAME_service_inspection:** days and distance before the next inspection, whichever is reached first.
* **sensor.NAME_oil_inspection:** days and distance before the next oil change, whichever is reached first. Cars with combustion engines only.
* **sensor.NAME_last_connected:** timestamp indicating the last time the car was connected to We Connect.
* **sensor.NAME_charging_time_left:** estimated time until charging has finished. BEVs and PHEVs only.
* **sensor.NAME_electric_range:** estimated electric range of the car. BEVs and (P)HEVs only.
* **sensor.NAME_combustion_range:** estimated fuel range of the car. Cars with combustion engines only.
* **sensor.NAME_combined_range:** estimated total range of the car.
* **sensor.NAME_charge_max_ampere:** the maximum current the car is configured to draw from AC. BEVs and PHEVs only.
* **sensor.NAME_climatisation_target_temperature:** the temperature the car will climatise to when climatisation is started.
* **binary_sensor.NAME_external_power:** whether the car is pluggin into an active charger. BEVs and PHEVs only.
* **binary_sensor.NAME_parking_light:** whether the parking lights are on.
* **binary_sensor.NAME_climatisation_without_external_power:** whether the car would pre-heat or cool when not plugged in.
* **binary_sensor.NAME_doors_locked:** whether the car's doors are locked.
* **binary_sensor.NAME_trunk_closed:** whether the car's trunk are closed.
* **lock.NAME_door_locked:** indicates and controls the car's door lock. Requires S-PIN to control.
* **lock.NAME_trunk_locked:** indicates and controls the car's trunk lock. Requires S-PIN to control.
* **switch.NAME_request_in_progress:** indicates whether the plugin is currently updating its data from We Connect. Can be turned on to force an update.
* **binary_sensor.NAME_windows_closed:** whether the car's windows are closed.
* **binary_sensor.NAME_sunroof_closed:** whether the car's sunroof is closed.
* **sensor.NAME_last_trip_average_speed:** average speed on the last trip.
* **sensor.NAME_last_trip_average_fuel_consumption:** average fuel consuption on the last trip.
* **sensor.NAME_last_trip_average_electric_consumption:** average electric motor consumption on the last trip.
* **sensor.NAME_last_trip_recuperation:** average electric recuperation on the last trip. BEVs and (P)HEVs only.
* **sensor.NAME_last_trip_average_auxillary_consumption:** average auxillary consumption by heating, air con... on the last trip. BEVs only.
* **sensor.NAME_last_trip_total_electric_consumption:** average total electric consumption on the last trip. BEVs and (P)HEVs only.
* **sensor.NAME_last_trip_duration:** duration of the last trip.

![alt text](https://user-images.githubusercontent.com/12171819/55963464-30216480-5c73-11e9-9b91-3bf06672ef36.png)

## Automations

In this example we are sending notifications to an ios device

Save these automations in your automations file `<config dir>/automations.yaml`

### Get notification when your car is on a new place and show a map with start position and end position
```yaml
- id: notify_volkswagen_position_change
  description: Notify when position has been changed
  alias: VW position changed notification
  trigger:
    - platform: state
      entity_id: device_tracker.vw_carid
  action:
    - service: notify.ios_my_ios_device
      data_template:
        title: "Passat GTE Position Changed"
        message: |
          🚗 VW Car is now on a new place.
        data:
          url: /lovelace/car
          apns_headers:
            'apns-collapse-id': 'car_position_state_{{ trigger.entity_id.split(".")[1] }}'
          push:
            category: map
            thread-id: "HA Car Status"
          action_data:
            latitude: "{{trigger.from_state.attributes.latitude}}"
            longitude: "{{trigger.from_state.attributes.longitude}}"
            second_latitude: "{{trigger.to_state.attributes.latitude}}"
            second_longitude: "{{trigger.to_state.attributes.longitude}}"
            shows_traffic: true
```

### Get notification when your car has started/stopped climatisation
```yaml
- id: notify_volkswagen_climatisation
  description: Notify when climatisation state changes
  alias: VW climatisation notifications
  trigger:
    - platform: state
      entity_id: switch.vw_carid_electric_climatisation
      from: 'off'
      to: 'on'
    - platform: state
      entity_id: switch.vw_carid_electric_climatisation
      from: 'on'
      to: 'off'
  action:
    - service: notify.ios_my_ios_device
      data_template:
        title: "VW Car Climatisation State"
        message: |
          🚗 VW Climatisation has {% if trigger.to_state.state == 'on' %}been started{% else %}stopped{% endif %}.
        data:
          url: /lovelace/car
          apns_headers:
            'apns-collapse-id': 'car_climatisation_state_{{ trigger.entity_id.split(".")[1] }}'
          push:
            thread-id: "HA Car Status"
```

### Get notification when your car has started/stopped charging
```yaml
- id: notify_volkswagen_charging
  description: Notify when charging state changes
  alias: VW charging notifications
  trigger:
    - platform: state
      entity_id: switch.vw_carid_charging
      from: 'off'
      to: 'on'

    - platform: state
      entity_id: switch.vw_carid_charging
      from: 'on'
      to: 'off'
  action:
    # delay so charging time gets updated
    - delay: '00:00:05'
    - service: notify.ios_my_ios_device
      data_template:
        title: "VW Car Charging State"
        message: |
          🚗 VW {% if trigger.to_state.state == 'on' %}is now charging{% else %}has stopped charging{% endif %}.
          {% if trigger.to_state.state == 'on' %}⏰ {{ states('sensor.vw_carid_charging_time_left_2') }} minutes untill battery is fully charged.{% endif %}
        data:
          url: /lovelace/car
          apns_headers:
            'apns-collapse-id': 'car_charging_state_{{ trigger.entity_id.split(".")[1] }}'
          push:
            thread-id: "HA Car Status"
```

### Get notification when your car has full battery
```yaml
- id: notify_volkswagen_battery_full
  description: Notify when battery is fully charged
  alias: VW battery level full Notifications
  trigger:
    - platform: numeric_state
      entity_id: sensor.vw_carid_battery_level
      above: 99
  action:
    - service: notify.ios_my_ios_device
      data_template:
        title: "Passat GTE Fully Charged"
        message: |
          🚗 VW is now fully charged.
        data:
          url: /lovelace/car
          apns_headers:
            'apns-collapse-id': 'car_battery_state_{{ trigger.entity_id.split(".")[1] }}'
          push:
            thread-id: "HA Car Status"
```

### Announce when your car is unlocked but no one is home
```yaml
- id: 'notify_volkswagen_car_is_unlocked'
  alias: VW is at home and unlocked
  trigger:
    - entity_id: binary_sensor.vw_carid_external_power
      platform: state
      to: 'on'
      for: 00:10:00
  condition:
    - condition: state
      entity_id: lock.vw_carid_door_locked
      state: unlocked
    - condition: state
      entity_id: device_tracker.my_device
      state: home
    - condition: time
      after: '07:00:00'
      before: '21:00:00'
  action:
    # Notification via push message to smartphone
    - service: notify.device
      data:
        message: "The car is unlocked!"
        target:
          - device/my_device
    # Notification via smart speaker (kitchen)
    - service: media_player.volume_set
      data:
        entity_id: media_player.kitchen
        volume_level: '0.6'
    - service: tts.google_translate_say
      data:
        entity_id: media_player.kitchen
        message: "My Lord, the car is unlocked. Please attend this this issue at your earliest inconvenience!"
```

## Enable debug logging
```yaml
logger:
    default: info
    logs:
        volkswagencarnet: debug
        dashboard: debug
        custom_components.volkswagencarnet: debug
        custom_components.volkswagencarnet.climate: debug
        custom_components.volkswagencarnet.lock: debug
        custom_components.volkswagencarnet.device_tracker: debug
        custom_components.volkswagencarnet.switch: debug
        custom_components.volkswagencarnet.binary_sensor: debug
        custom_components.volkswagencarnet.sensor: debug
 ```

## Lovelace Card

Check out this awesome lovelace card by endor
https://github.com/endor-force/lovelace-carnet

![alt text](https://user-images.githubusercontent.com/12171819/55963632-7d9dd180-5c73-11e9-9eea-c2b211f6843b.png)
