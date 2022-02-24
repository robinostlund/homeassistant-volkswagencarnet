"""
Support for Volkswagen WeConnect Platform
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

import pytz

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import ToggleEntity, EntityCategory

from . import VolkswagenEntity, VolkswagenData
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Setup the volkswagen switch."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenSwitch(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenSwitch(
                data,
                coordinator.vin,
                instrument.component,
                instrument.attr,
                hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (instrument for instrument in data.instruments if instrument.component == "switch" and not instrument.attr.startswith("departure_timer"))
        )
        async_add_devices(
            VolkswagenDepartureTimer(
                data,
                coordinator.vin,
                instrument.component,
                instrument.attr,
                hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (instrument for instrument in data.instruments if instrument.component == "switch" and instrument.attr.startswith("departure_timer"))
        )

    return True


class VolkswagenSwitch(VolkswagenEntity, ToggleEntity):
    """Representation of a Volkswagen WeConnect Switch."""

    def __init__(self, data: VolkswagenData, vin: str, component: str, attribute: str, callback=None):
        super().__init__(data, vin, component, attribute, callback)

    def turn_on(self, **kwargs: Any) -> None:
        raise NotImplementedError

    def turn_off(self, **kwargs: Any) -> None:
        raise NotImplementedError

    @property
    def is_on(self):
        """Return true if switch is on."""
        _LOGGER.debug("Getting state of %s" % self.instrument.attr)
        return self.instrument.state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning ON %s." % self.instrument.attr)
        await self.instrument.turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning OFF %s." % self.instrument.attr)
        await self.instrument.turn_off()
        self.async_write_ha_state()

    @property
    def assumed_state(self):
        return self.instrument.assumed_state

    @property
    def extra_state_attributes(self) -> Optional[dict[str, Any]]:
        return {**super().extra_state_attributes, **self.instrument.attributes}


class VolkswagenDepartureTimer(VolkswagenSwitch):

    def turn_on(self, **kwargs: Any) -> None:
        super().turn_on()

    def turn_off(self, **kwargs: Any) -> None:
        super().turn_off()

    def __init__(self, data: VolkswagenData, vin: str, component: str, attribute: str, callback=None):
        super().__init__(data, vin, component, attribute, callback)
        _LOGGER.debug("Departure Timer initialized")

    @property
    def device_class(self) -> str:
        return "departure_timer"

    @property
    def entity_category(self) -> Union[EntityCategory, str, None]:
        return EntityCategory.CONFIG

    @property
    def extra_state_attributes(self) -> Optional[dict[str, Any]]:
        attribs = super(VolkswagenSwitch, self).extra_state_attributes
        if "departure_time" in attribs:
            if re.match(r"^\d\d:\d\d$", attribs["departure_time"]):
                d = datetime.now()
                d = d.replace(
                    hour=int(attribs["departure_time"][0:2]),
                    minute=int(attribs["departure_time"][3:5]),
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc
                ).astimezone(pytz.timezone(self.hass.config.time_zone))
                attribs["departure_time"] = d.strftime("%H:%M")
            else:
                d = datetime.strptime(attribs["departure_time"], "%Y-%m-%dT%H:%M")\
                    .replace(tzinfo=timezone.utc, second=0, microsecond=0)
                attribs["departure_time"] = d
        return attribs
