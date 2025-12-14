[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/github/v/release/robinostlund/homeassistant-volkswagencarnet)
![PyPi](https://img.shields.io/pypi/v/volkswagencarnet?label=latest%20pypi)
![Downloads](https://img.shields.io/github/downloads/robinostlund/homeassistant-volkswagencarnet/total)
![CodeStyle](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![Known Vulnerabilities](https://snyk.io/test/github/robinostlund/homeassistant-volkswagencarnet/badge.svg)
[![CodeQL](https://github.com/robinostlund/homeassistant-volkswagencarnet/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/robinostlund/homeassistant-volkswagencarnet/actions/workflows/codeql-analysis.yml)



# Volkswagen Connect - An Home Assistant custom component to interact with the VW Connect service. (EU ONLY)

[![buy me a coffee](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/robinostlund)

[![buy me a coffee](https://raw.githubusercontent.com/robinostlund/homeassistant-volkswagencarnet/master/resources/stickpin_kofi.jpeg)](https://ko-fi.com/stickpin)

## Description

Welcome to Volkswagen Connect custom component designed for [Home Assistant](https://www.home-assistant.io) with the capability to interact with the Volkswagen Connect service (your car).

This custom component supports the **Volkswagen Connect cars** such as the Passat, Golf, e-Golf, Tiguan, ID etc. It requires you to have an active and working VW online subscription connected to your car. The new electric vehicles such as the ID series are supported as well.

Most of the functionality found the "Volkswagen Connect app" should be available via this integration, this includes options such as auxiliary heater control.

Please note that there has only been reports of success with this component for cars sold (and based) in the EU. Please feel free to contribue to make this component work in the US as well, we do not have access to any Volkswagen Connect accounts to verify at this stage.

## Having issues with this custom component?
Please, before posting an issue make sure that VW´s Connect service works for you via a normal web browser. Not only the login part but also make sure that the VW Connect service interacts with the car proper, including updating of all sensors and location. If there are problems with the VW Connect service this component will not work either. This custom component is only as good as the VW Connect service.

## Installation

### Upgrading from an old component version
* Remove all configuration from Home Assistants config file configuration.yaml
* Upgrade the component via HACS or manually replace the files in the custom_component folder (see install manually below)
* Restart Home Assistant
* Add the component again as per below (install+configuration)

### Install with HACS (recommended)
Do you you have [HACS](https://community.home-assistant.io/t/custom-component-hacs) installed? Just search for Volkswagen Connect and install it direct from HACS. HACS will keep track of updates and you can easly upgrade this component to latest version.

### Install manually
Make sure you have an account on Volkswagen Connect.

Clone or copy the repository and copy the folder 'homeassistant-volkswagencarnet/custom_component/volkswagencarnet' into '<config dir>/custom_components'

#### Installing dependencies
Note that only the packaged releases (zip file) have the dependencies configured so that Home Assistant can find them automatically, but if you use the source code or git branch, you need to manually install the correct versions of all dependencies also using something like `pip install -r requirements.txt`.

## Configuration
* Restart Home Assistant
* Add and configure the component via the UI: Configuration > Integrations > search for "Volkswagen Connect" and follow the wizard to configure (use your Volkswagen Connect credentials)
* All available features of your car should be added automatically after you have selected the VIN

### Configuration flow settings
* Name your car - Enter a custom name, defaults to VIN (Optional)
* Username/Password - Volkswagen Connect (Required)
* Region - The country where the car was sold (Required)
* Mutable - If enabled you can interact with the car, if disabled only data from the car will be presented (Optional)
* S-PIN - Required for some specific options such as lock/unlock (Optional)
* Distance unit conversion - Select if you wish to use "Swedish mil" or Imperial Miles instead of KM (Optional, default is KM)
![image](https://raw.githubusercontent.com/robinostlund/homeassistant-volkswagencarnet/master/resources/integration_config.png)

Note that the Volkswagen API has a connection limit of 480 calls/day (one call every 3rd minute). The default interval of 5 minutes in this integration will leave only 192 calls for other applications, such as the VW app, which might not be enough. If you want to use the app alongside this integration, it is recommended to raise this interval to 10 minutes. This can be changed by selecting **Configure** for the integration in Home Assistant, and them modifying the value **Sensors update interval (minutes)**.

## Entities

This plugin creates entities in the format `DOMAIN.NAME_ENTITY`. Not all entities are created for all make, year and models, for example pure electric cars will not have entities only applicable to cars with a combustion engine.

## Enable debug logging

Check out this Wiki page:
https://github.com/robinostlund/homeassistant-volkswagencarnet/wiki/Enabling-Debug-Logging-in-Home-Assistant

## Lovelace Card

Check out this awesome lovelace card by endor
https://github.com/endor-force/lovelace-carnet

![alt text](https://user-images.githubusercontent.com/12171819/55963632-7d9dd180-5c73-11e9-9eea-c2b211f6843b.png)

## Guides
Tristan created a german video how to setup and use this integration. It also includes some automation in Node-RED. https://youtu.be/91223AtNvVc
