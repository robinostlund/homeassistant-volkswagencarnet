[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/github/v/release/robinostlund/homeassistant-volkswagencarnet)
![PyPi](https://img.shields.io/pypi/v/volkswagencarnet?label=latest%20pypi)
![Downloads](https://img.shields.io/github/downloads/robinostlund/homeassistant-volkswagencarnet/total)
![CodeStyle](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![Known Vulnerabilities](https://snyk.io/test/github/robinostlund/homeassistant-volkswagencarnet/badge.svg)
[![CodeQL](https://github.com/robinostlund/homeassistant-volkswagencarnet/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/robinostlund/homeassistant-volkswagencarnet/actions/workflows/codeql-analysis.yml)



# Volkswagen Connect - An Home Assistant custom component to interact with the VW Connect service. (EU ONLY)

## Support the Project

_If you enjoy this integration and would like to support its development, buying us a coffee is always appreciated_  ☕

| Original Author (robinostlund) | [![Buy me a coffee](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/robinostlund) |
|------|----------------|
| Project Maintainer (stickpin) | [![Buy me a Ko-Fi](https://raw.githubusercontent.com/robinostlund/homeassistant-volkswagencarnet/master/resources/stickpin_kofi.jpeg)](https://ko-fi.com/stickpin) |

## Description

Welcome to the **Volkswagen Connect** custom component for [Home Assistant](https://www.home-assistant.io), allowing you to interact with the Volkswagen Connect service and your car.

This component supports **Volkswagen Connect vehicles** such as the Passat, Golf, e-Golf, Tiguan, ID series, and more. An active VW online subscription connected to your car is required. New electric vehicles, including the ID series, are also supported.

Most of the features available in the official "Volkswagen Connect" app are accessible through this integration.

> **Note:** So far, this component has only been reported to work successfully with cars sold in the **EU**. Contributions to support vehicles outside the EU, such as in the US, are welcome. Currently, we do not have access to non-EU VW Connect accounts to verify functionality.

## Installation

### Install with HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=robinostlund&repository=homeassistant-volkswagencarnet&category=Integration)

Or, search for `Volkswagen Connect` in HACS and install it under the **Integrations** category.

1. Restart Home Assistant.
2. In the Home Assistant UI, go to **Settings → Integrations**, click **+ Add Integration**, and search for **Volkswagen Connect**.

HACS will track updates automatically, making it easy to upgrade this component to the latest version.

### Manual Installation

<details>
<summary>More Details</summary>

- Download the `volkswagencarnet.zip` file from the latest [published release](https://github.com/robinostlund/homeassistant-volkswagencarnet/releases).
- Extract the contents of `custom_components` into the `<config directory>/custom_components` folder of your Home Assistant installation.
- Restart Home Assistant.
- In the Home Assistant UI, go to **Settings → Integrations**, click **+ Add Integration**, and search for **Volkswagen Connect**.

Note that only the packaged releases (zip file) have the dependencies configured so that Home Assistant can find them automatically, but if you use the source code or git branch, you need to manually install the correct versions of all dependencies also using something like `pip install -r requirements.txt`.

</details>

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

> **Note:** The Volkswagen API has a connection limit of **480 calls per day** (approximately one call every 3 minutes). The default update interval of **5 minutes** in this integration will use 288 calls per day, leaving only **192 calls** available for other applications, such as the official VW app — which may not be sufficient. If you plan to use the VW app alongside this integration, it is recommended to **increase the update interval to 10 minutes**. You can adjust this by going to the integration in Home Assistant, selecting **Configure**, and then modifying the **Sensors update interval (minutes)**.

## Having Issues with This Component?

Before creating an issue, please ensure that the VW Connect service works properly for your account via a web browser. Check not only login but also that the service interacts with your car correctly, including sensor updates and location tracking. 

This component relies entirely on the VW Connect service — if their service is experiencing issues, this integration will not function. It is only as reliable as the VW Connect platform itself.

## Enable debug logging

Check out this Wiki page:
https://github.com/robinostlund/homeassistant-volkswagencarnet/wiki/Enabling-Debug-Logging-in-Home-Assistant

## Acknowledgements

A heartfelt thank you to all contributors - your code, feedback, testing, and support are what keep this project moving forward.

Every contribution, big or small, is truly appreciated! ❤️