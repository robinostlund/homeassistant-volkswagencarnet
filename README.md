Volkswagen Carnet - An home assistant plugin to add integration with your car
============================================================
Information
------------
This plugin is still in developing state.

Installation
------------

Make sure you have a account on volkswagen carnet.

Clone or copy the root of the repository into `<config dir>/custom_components`

Add a volkswagen_carnet configuration block to your `<config dir>/configuration.yaml`

Start the Home Assistant service with the configuration below, check "states" in Home Assistant to find out your CarNet ID, replace vw_carid with your ID throughout the example configuration below, save the config files and restart Home Assistant.

```switch.vw_carid_charging ---> switch.wvwzzzXczheXXXXXXX_charging```


```yaml
volkswagen_carnet:
    username: <username to volkswagen carnet>
    password: <password to volkswagen carnet>
    update_interval: 
        minutes: 3 # specify in minutes how often to fetch status data from carnet (optional, default 3 min, minimum 2 min)
```

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
  
volkswagensensors:
    name: Volkswagen Information
    control: hidden
    entities:
        - sensor.vw_carid_battery_level
        - sensor.vw_carid_charging_time_left
        - sensor.vw_carid_odometer
        - sensor.vw_carid_electric_range
        - sensor.vw_carid_last_connected
        - sensor.vw_carid_service_inspection
        - sensor.vw_carid_climatisation_target_temperature
        - binary_sensor.vw_carid_parking_light
        - binary_sensor.vw_carid_external_power
        
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
binary_sensor.vw_carid_external_power:
    friendly_name: VW Car External Power Connected
device_tracker.vw_carid:
    friendly_name: VW Car Location
lock.vw_carid_doors_locked:
    friendly_name: VW Car Locked
    assumed_state: false
sensor.vw_carid_battery_level:
    friendly_name: VW Car Battery Level
sensor.vw_carid_fuel_level:
    friendly_name: VW Car Fuel Level
sensor.vw_carid_charging_time_left:
    friendly_name: VW Car Charging time left
sensor.vw_carid_odometer:
    friendly_name: VW Car Odometer
sensor.vw_carid_electric_range:
    friendly_name: VW Car Electric Range Left
sensor.vw_carid_combustion_range:
    friendly_name: VW Car Combustion Range Left
sensor.vw_carid_last_connected:
    friendly_name: VW Car Last Connected
sensor.vw_carid_service_inspection:
    friendly_name: VW Car Next Service
sensor.vw_carid_climatisation_target_temperature:
    friendly_name: VW Car Climatisation Target Temperature
switch.vw_carid_charging:
    friendly_name: VW Car Charging
    assumed_state: false
switch.vw_carid_climatisation:
    friendly_name: VW Car Climatisation
    assumed_state: false
switch.vw_carid_window_heater:
    friendly_name: VW Car Window Heating
    assumed_state: false
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