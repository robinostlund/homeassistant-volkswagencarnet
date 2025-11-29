"""Lock support for Volkswagen Connect Platform."""

import logging

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant

from . import VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    """Perform platform setup."""
    if discovery_info is None:
        return

    async_add_entities([VolkswagenLock(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Perform entity setup."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenLock(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
            )
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "lock"
            )
        )

    return True


class VolkswagenLock(VolkswagenEntity, LockEntity):
    """Represents a Volkswagen Connect Lock."""

    # Entity attributes (Home Assistant 2024+)
    _attr_has_entity_name = True

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        _LOGGER.debug("Getting state of %s", self.instrument.attr)
        return self.instrument.is_locked

    async def async_lock(self, **kwargs: object) -> None:
        """Lock the car."""
        try:
            await self.instrument.lock()
            self.notify_updated()
        except Exception as err:
            _LOGGER.error("Failed to lock %s: %s", self.instrument.attr, err)
            raise

    async def async_unlock(self, **kwargs: object) -> None:
        """Unlock the car."""
        try:
            await self.instrument.unlock()
            self.notify_updated()
        except Exception as err:
            _LOGGER.error("Failed to unlock %s: %s", self.instrument.attr, err)
            raise
