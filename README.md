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

```switch.vw_carid_charge ---> switch.vw_wvwzzzXczheXXXXXXX_charge```


```yaml
volkswagen_carnet:
    username: <username to volkswagen carnet>
    password: <password to volkswagen carnet>

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

volkswagenswitches:
    name: Volkswagen Switches
    control: hidden
    entities:
        - switch.vw_carid_charge
        - switch.vw_carid_climat
        - switch.vw_carid_melt
        - device_tracker.vw_carid
  
volkswagensensors:
    name: Volkswagen Sensors
    control: hidden
    entities:
        - sensor.vw_carid_battery
        - sensor.vw_carid_charge_max_ampere
        - sensor.vw_carid_charging_time_left
        - sensor.vw_carid_climat_target_temperature
        - sensor.vw_carid_distance
        - sensor.vw_carid_electric_range_left
        - sensor.vw_carid_external_power_connected
        - sensor.vw_carid_last_update
        - sensor.vw_carid_locked
```

Customize example
------------
`<config dir>/customize.yaml`
```yaml
switch.vw_carid_charge:
    friendly_name: VW Car Charging
switch.vw_carid_climat:
    friendly_name: VW Car Climatisation
switch.vw_carid_melt:
    friendly_name: VW Car Window Heating
device_tracker.vw_carid:
    friendly_name: VW Car Location
sensor.vw_carid_battery:
    friendly_name: VW Car Battery
sensor.vw_carid_charge_max_ampere:
    friendly_name: VW Car Max Ampere
sensor.vw_carid_charging_time_left:
    friendly_name: VW Car Charging time left
sensor.vw_carid_climat_target_temperature:
    friendly_name: VW Car Climatisation Target Temperature
sensor.vw_carid_distance:
    friendly_name: VW Car Odometer
sensor.vw_carid_electric_range_left:
    friendly_name: VW Car Electric Range Left
sensor.vw_carid_external_power_connected:
    friendly_name: VW Car External Power Connected
sensor.vw_carid_last_update:
    friendly_name: VW Car Last Updated
sensor.vw_carid_locked:
    friendly_name: VW Car Locked
```
