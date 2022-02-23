"""
"""
import logging
from typing import Optional

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry
from volkswagencarnet.vw_vehicle import Vehicle

from .const import DOMAIN
from .error import ServiceError

_LOGGER = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, hass: HomeAssistant):
        self.hass: HomeAssistant = hass

    async def set_timer_basic_settings(self, service_call: ServiceCall):
        # find VIN
        c = await self.get_coordinator(service_call)
        _LOGGER.debug(F"Found VIN {c.vin}")
        # parse service call
        tt = service_call.data.get("target_temperature", None)
        ml = service_call.data.get("min_level", None)
        res = True

        v: Optional[Vehicle] = None
        for vehicle in c.connection.vehicles:
            if vehicle.vin.upper() == c.vin:
                v = vehicle
                break
        if v is None:
            raise Exception("Vehicle not found")

        # update timers accordingly
        if tt is not None:
            # get timers
            t = await c.connection.getTimers(c.vin)
            _LOGGER.debug(f"Setting target temperature to {tt} {self.hass.config.units.temperature_unit}")
            if self.hass.config.units.is_metric:
                t.timersAndProfiles.timerBasicSetting.set_target_temperature_celsius(float(tt))
            else:
                t.timersAndProfiles.timerBasicSetting.set_target_temperature_fahrenheit(int(tt))
            # send command to volkswagencarnet
            res = await v.set_climatisation_temp(t.timersAndProfiles.timerBasicSetting.targetTemperature)
        if ml is not None:
            _LOGGER.debug(f"Setting minimum charge level to {ml}%")
            # send charge limit command to volkswagencarnet
            res = res and await v.set_charge_min_level(ml)
        return res

    async def get_coordinator(self, service_call: ServiceCall):
        """Find VIN for device."""
        registry: DeviceRegistry = device_registry.async_get(self.hass)
        dev_entry: DeviceEntry = registry.async_get(service_call.data.get("device_id"))

        # Get coordinator handling the device entry
        config_entry = self.hass.config_entries.async_get_entry(list(dev_entry.config_entries)[0])
        if config_entry.domain != DOMAIN:
            raise ServiceError("Unknown entity")
        coordinator = config_entry.data.get(
            'coordinator',
        )
        if coordinator is None:
            coordinator = self.hass.data[DOMAIN][config_entry.entry_id]['data'].coordinator
        if coordinator is None:
            raise ServiceError("Unknown entity")
        return coordinator
