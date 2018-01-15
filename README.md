Volkswagen Carnet - An home assistant plugin to add integration with your car
============================================================
Information
------------
This plugin is still in developing state. And multiple vehicle support hasn't yet been added.

Installation
------------

Make sure you have a account on volkswagen carnet.

Clone or copy the root of the repository into `<config dir>/custom_components`

Add a volkswagen_carnet configuration block to your `<config dir>/configuration.yaml`

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
  - group.volkswagen

volkswagen:
 name: Volkswagen Switches
 control: hidden
 entities:
  - switch.vw_carid_charge
  - switch.vw_carid_climat
  - switch.vw_carid_melt
  - device_tracker.vw_carid
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
```
