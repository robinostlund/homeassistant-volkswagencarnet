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

Add a volkswagencarnet configuration block to your `<config dir>/configuration.yaml`
```yaml
volkswagencarnet:
    username: <username to volkswagen carnet>
    password: <password to volkswagen carnet>
    scan_interval: 
        minutes: 2
    name:
        wvw1234567812356: 'Passat GTE'
```

scan_interval: specify in minutes how often to fetch status data from carnet (optional, default 5 min, minimum 1 min)

name: set a friendly name of your car you can use the name setting as in confiugration example.

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
