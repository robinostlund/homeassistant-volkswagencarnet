Volkswagen Carnet - An home assistant plugin to add integration with your car
============================================================
Description
------------
This platform plugin allows you to see some information from volkswagen carnet related to your car that has a valid carnet subscription.

It also allows you to trigger some functions like start climatisation if your car supports that.

Installation
------------

Make sure you have a account on volkswagen carnet.

Clone or copy the root of the repository into `<config dir>/custom_components`

Add a volkswagen_carnet configuration block to your `<config dir>/configuration.yaml`
```yaml
volkswagen_carnet:
    username: <username to volkswagen carnet>
    password: <password to volkswagen carnet>
    update_interval: 
        minutes: 5 # specify in minutes how often to fetch status data from carnet (optional, default 3 min, minimum 3 min)
```

Start the Home Assistant service with the configuration below, check "states" in Home Assistant to find out your CarNet ID, replace vw_carid with your ID throughout the example configuration below, save the config files and restart Home Assistant.

Example: ```switch.vw_carid_charging ---> switch.wvwzzzXczheXXXXXXX_charging```

Group example
------------
`<config dir>/groups.yaml`
```yaml
volkswagendashboard:
    name: Volkswagen
    view: yes
    icon: mdi:car
    entities:
        - group.volkswagenswitches
        - group.volkswagensensors
        - group.volkswagenlocation

volkswagenswitches:
    name: Volkswagen Switches
    control: hidden
    entities:
        - switch.vw_carid_charging
        - switch.vw_carid_climatisation
        - switch.vw_carid_window_heater
        - lock.vw_carid_doors_locked
        - lock.vw_carid_trunk_locked
  
volkswagensensors:
    name: Volkswagen Information
    control: hidden
    entities:
        - sensor.vw_carid_battery_level
        - sensor.vw_carid_fuel_level
        - sensor.vw_carid_charging_time_left
        - sensor.vw_carid_odometer
        - sensor.vw_carid_electric_range
        - sensor.vw_carid_combustion_range
        - sensor.vw_carid_combined_range
        - sensor.vw_carid_last_connected
        - sensor.vw_carid_service_inspection
        - sensor.vw_carid_climatisation_target_temperature
        - binary_sensor.vw_carid_parking_light
        - binary_sensor.vw_carid_external_power
        - binary_sensor.vw_carid_climatisation_without_external_power
        
volkswagenlocation:
    name: Volkswagen Location
    control: hidden
    entities:
        - device_tracker.vw_carid
```

Customize example
------------
`<config dir>/customize.yaml`
```yaml
binary_sensor.vw_carid_parking_light:
    friendly_name: VW Car Parking Lights
    show_last_changed: true
binary_sensor.vw_carid_external_power:
    friendly_name: VW Car External Power Connected
    show_last_changed: true
binary_sensor.vw_carid_climatisation_without_external_power:
    friendly_name: VW Car Climatisation Without External Power
    show_last_changed: true
device_tracker.vw_carid:
    friendly_name: VW Car Location
    show_last_changed: true
lock.vw_carid_doors_locked:
    friendly_name: VW Car Locked
    assumed_state: false
    hide_control: true
    show_last_changed: true
lock.vw_carid_trunk_locked:
    friendly_name: VW Trunk Locked
    assumed_state: false
    hide_control: true
    show_last_changed: true
sensor.vw_carid_battery_level:
    friendly_name: VW Car Battery Level
    show_last_changed: true
sensor.vw_carid_fuel_level:
    friendly_name: VW Car Fuel Level
    show_last_changed: true
sensor.vw_carid_charge_max_ampere:
    friendly_name: VW Charge max ampere
    show_last_changed: true
sensor.vw_carid_charging_time_left:
    friendly_name: VW Car Charging time left
    show_last_changed: true
sensor.vw_carid_odometer:
    friendly_name: VW Car Odometer
    show_last_changed: true
sensor.vw_carid_electric_range:
    friendly_name: VW Car Electric Range Left
    show_last_changed: true
sensor.vw_carid_combustion_range:
    friendly_name: VW Car Combustion Range Left
    show_last_changed: true
sensor.vw_carid_combined_range:
    friendly_name: VW Car Combined Range Left
    show_last_changed: true
sensor.vw_carid_last_connected:
    friendly_name: VW Car Last Connected
    show_last_changed: true
sensor.vw_carid_service_inspection:
    friendly_name: VW Car Next Service
    show_last_changed: true
sensor.vw_carid_climatisation_target_temperature:
    friendly_name: VW Car Climatisation Target Temperature
    show_last_changed: true
switch.vw_carid_charging:
    friendly_name: VW Car Charging
    assumed_state: false
    show_last_changed: true
switch.vw_carid_climatisation:
    friendly_name: VW Car Climatisation
    assumed_state: false
    show_last_changed: true
switch.vw_carid_window_heater:
    friendly_name: VW Car Window Heating
    assumed_state: false
    show_last_changed: true
```

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
        custom_components.volkswagen_carnet: debug
        custom_components.lock.volkswagen_carnet: debug
        custom_components.sensor.volkswagen_carnet: debug
        custom_components.switch.volkswagen_carnet: debug
        custom_components.device_tracker.volkswagen_carnet: debug
 ```