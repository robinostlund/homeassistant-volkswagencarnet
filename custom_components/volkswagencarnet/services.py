"""
"""
import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry

from .error import ServiceError
from .const import DOMAIN, DATA_KEY

_LOGGER = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, hass: HomeAssistant):
        self.hass: HomeAssistant = hass

    async def set_timer_basic_settings(self, service_call: ServiceCall):
        # find VIN
        c = await self.get_coordinator(service_call)
        _LOGGER.debug(F"Found VIN {c.vin}")
        # get timers
        t = await c.connection.getTimers(c.vin)
        # parse service call
        tc = service_call.data.get("target_temperature_celsius", None)
        tf = service_call.data.get("target_temperature_fahrenheit", None)
        ml = service_call.data.get("min_level", None)
        # update timers accordingly
        if tc is not None:
            _LOGGER.debug(f"Setting target temperature to {tc} C")
            t.timersAndProfiles.timerBasicSetting.set_target_temperature_celsius(float(tc))
        elif tf is not None:
            _LOGGER.debug(f"Setting target temperature to {tf} F")
            t.timersAndProfiles.timerBasicSetting.set_target_temperature_fahrenheit(int(tf))
        if tc is not None or tf is not None:
            # send command to volkswagencarnet
            c.connection.setTimersAndProfiles(t)
        if ml is not None:
            _LOGGER.debug(f"Setting minimum charge level to {ml}%")
            # send charge limit command to volkswagencarnet
            c.connection.setChargeMinLevel(c.vin, ml)

    async def get_coordinator(self, service_call: ServiceCall):
        """Find VIN for device."""
        registry: DeviceRegistry = device_registry.async_get(self.hass)
        dev_entry: DeviceEntry = registry.async_get(service_call.data.get("device_id"))

        # Get coordinator handling the device entry
        config_entry = self.hass.config_entries.async_get_entry(list(dev_entry.config_entries)[0])
        if config_entry.domain != DOMAIN:
            raise ServiceError("Unknown entity")
        coordinator = config_entry.data.get('coordinator')
        if coordinator is None:
            raise ServiceError("Unknown entity")
        return coordinator

    async def get_vehicle(self, vin: str):
        # return coordinator.conection.vehicle(vin)
        pass
