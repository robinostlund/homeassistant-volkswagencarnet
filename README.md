[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
![Version](https://img.shields.io/github/v/release/robinostlund/homeassistant-volkswagencarnet)
![PyPi](https://img.shields.io/pypi/v/volkswagencarnet?label=latest%20pypi)
![Downloads](https://img.shields.io/github/downloads/robinostlund/homeassistant-volkswagencarnet/total)


# Volkswagen We Connect - An Home Assistant custom component to interact with the We Connect service

[![buy me a coffee](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/robinostlund)

## Login issues with some countries and regions - Please help us!
Update as of 2021-05-03 - Login issues for EU/EMEA based accounts has now been resolved with the release of version .41.

### Confirmed working regions and countries
Region | Country | Country Code
--- | --- | ---
EMEA | All | DE

### To be confirmed regions and countries - we need more info
We are still looking for server URLs for Asia/Pacific, South and North America. Please see information here: https://github.com/robinostlund/homeassistant-volkswagencarnet/issues/284

Region | Country | Country Code
--- | --- | ---
APAC | ? | ?
LAD | ? | ?
NA | ? | ?

## Description

Welcome to Volkswagen We Connect custom component designed for [Home Assistant](https://www.home-assistant.io) with the capability to interact with the Volkswagen We Connect service (your car).

This custom component supports the "non-ID" Volkswagen We Connect cars such as the Passat, Golf, e-Golf, Tiguan etc. It requires you to have an active and working VW online subscription connected to your car. For the new electric vehicles such as the ID series this component does not work. The new ID platform uses another backend system.

Most of the functionality found the "We Connect app" should be available via this integration, this includes options such as auxiliary heater control.

Note: Some features included in Volkswagen We Connect 2019 and newer are not fully tested. This custom component should work with any models such as Golf/Passat 8.5/Tiguan etc. But please bear with me and report any fault or error as an issue.

Please note that there has only been reports of success with this component for cars sold (and based) in the EU. Please feel free to contribue to make this component work in the US as well, we do not have access to any We Connect accounts to verify at this stage.

## Having issues with this custom component?
Please, before posting an issue make sure that VW´s WeConnect service works for you via a normal web browser. Not only the login part but also make sure that the VW WeConnect service interacts with the car proper, including updating of all sensors and location. If there are problems with the VW WeConnect service this component will not work either. This custom component is only as good as the VW WeConnect service.

## Installation

### Upgrading from an old component version
* Remove all configuration from Home Assistants config file configuration.yaml
* Upgrade the component via HACS or manually replace the files in the custom_component folder (see install manually below)
* Restart Home Assistant
* Add the component again as per below (install+configuration)

### Install with HACS (recommended)
Do you you have [HACS](https://community.home-assistant.io/t/custom-component-hacs) installed? Just search for Volkswagen We Connect and install it direct from HACS. HACS will keep track of updates and you can easly upgrade this component to latest version.

### Install manually
Make sure you have an account on Volkswagen We Connect.

Clone or copy the repository and copy the folder 'homeassistant-volkswagencarnet/custom_component/volkswagencarnet' into '<config dir>/custom_components'

## Configuration
* Restart Home Assistant
* Add and configure the component via the UI: Configuration > Integrations > search for "Volkswagen We Connect" and follow the wizard to configure (use your We Connect credentials)
* All available features of your car should be added automatically after you have selected the VIN

### Configuration flow settings
* Name your car - Enter a custom name, defaults to VIN (Optional)
* Username/Password - We Connect (Required)
* Region - The country where the car was sold (Required)
* Mutable - If enabled you can interact with the car, if disabled only data from the car will be presented (Optional)
* S-PIN - Required for some specific options such as lock/unlock (Optional)
* Distance unit conversion - Select if you wish to use "Swedish mil" or Imperial Miles instead of KM (Optional, default is KM)
![image](https://user-images.githubusercontent.com/53381142/117341181-b8e24d00-ae99-11eb-84af-7661e9170492.png)

## Entities

This plugin creates entities in the format `DOMAIN.NAME_ENTITY`. Not all entities are created for all make, year and models, for example pure electric cars will not have entities only applicable to cars with a combustion engine.

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

## Custom sensors

### Total electric consumption

This integration may only report the electrical engine consumption, recuperation and auxillary consumer consumption, but no combined total. This example template sensor implements the missing sensor. Add to configuration.yaml and replace [ID] by your car's name.

```yaml
sensor:
  - platform: template
    sensors:
      [ID]_last_trip_total_electric_consumption:
        value_template: >-
          {{ (   states('sensor.[ID]_last_trip_average_electric_engine_consumption') | float
               + states('sensor.[ID]_last_trip_average_auxillary_consumer_consumption') | float
               - states('sensor.[ID]_last_trip_average_recuperation') | float
             ) | round(1) }}
        unit_of_measurement: 'kWh/100km'
        friendly_name: '[ID] Last trip total electric consumption'
```

### Templates for converting distance from km to miles
As of v4.4.45 the same can be acheived by setting the distance units to Imperial in the integration configuration page.
![image](https://user-images.githubusercontent.com/53381142/117340592-f5fa0f80-ae98-11eb-9baa-1f5a0ef02848.png)

These templates create a new sensor with kilometers converted to miles. Add to your configuration.yaml and replace [ID] with your car's name. Note: these are for a BEV, other models may have different sensor names.

```yaml
  - platform: template
    sensors:
      [ID]_service_inspection_distance_miles:
        friendly_name: '[ID] Service inspection distance miles'
        value_template: "{{ (states('sensor.[ID]_service_inspection_distance').split(' ')[0] |int * 0.6213712) | round(0)}}"
        unique_id: [ID]inspectionmiles
        unit_of_measurement: mi
        icon_template: mdi:garage
      [ID]_combined_range_miles:
        friendly_name: '[ID] range miles'
        value_template: "{{ (states('sensor.[ID]_combined_range').split(' ')[0] |int * 0.6213712) | round(0)}}"
        unique_id: [ID]rangemiles
        unit_of_measurement: mi
        icon_template: mdi:car
      [ID]_odometer_miles:
        friendly_name: '[ID] Odometer miles'
        value_template: "{{ (states('sensor.[ID]_odometer').split(' ')[0] |int * 0.6213712) | round(0)}}"
        unique_id: [ID]odometermiles
        unit_of_measurement: mi
        icon_template: mdi:speedometer
      [ID]_last_trip_average_speed_miles:
        friendly_name: '[ID] Last trip average speed miles'
        value_template: "{{ (states('sensor.[ID]_last_trip_average_speed').split(' ')[0] |int * 0.6213712) | round(0)}}"
        unique_id: [ID]ltaspeedmi
        unit_of_measurement: mi/h
        icon_template: mdi:speedometer
      [ID]_last_trip_length_miles:
        friendly_name: '[ID] Last trip length miles'
        value_template: "{{ (states('sensor.[ID]_last_trip_length').split(' ')[0] |int * 0.6213712) | round(0)}}"
        unique_id: johnny5lasttriplengthmiles
        unit_of_measurement: mi
        icon_template: mdi:map-marker-distance
      [ID]_last_trip_average_electric_engine_consumption_miles:
        friendly_name: '[ID] Last trip average electric engine consumption miles'
        value_template: "{{ (states('sensor.[ID]_last_trip_average_electric_engine_consumption').split(' ')[0] |float * 0.6213712) | round(2)}}"
        unique_id: [ID]avgelectconmiles
        unit_of_measurement: kWh/100mi
        icon_template: mdi:car-battery
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
