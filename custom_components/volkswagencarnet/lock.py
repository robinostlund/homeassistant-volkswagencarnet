"""Lock support for Volkswagen WeConnect Platform."""

import logging
from typing import Any

from homeassistant.components.lock import LockEntity

from . import VolkswagenEntity
from .const import DATA_KEY, DATA, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Perform platform setup."""
    if discovery_info is None:
        return

    async_add_entities([VolkswagenLock(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
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
            for instrument in (instrument for instrument in data.instruments if instrument.component == "lock")
        )

    return True


class VolkswagenLock(VolkswagenEntity, LockEntity):
    """Represents a Volkswagen WeConnect Lock."""

    def lock(self, **kwargs: Any) -> None:
        """Not implemented."""
        raise NotImplementedError("Use async_lock instead")

    def unlock(self, **kwargs: Any) -> None:
        """Not implemented."""
        raise NotImplementedError("Use async_unlock instead")

    def open(self, **kwargs: Any) -> None:
        """Not implemented."""
        raise NotImplementedError

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        _LOGGER.debug("Getting state of %s" % self.instrument.attr)
        return self.instrument.is_locked

    async def async_lock(self, **kwargs):
        """Lock the car."""
        await self.instrument.lock()
        self.notify_updated()

    async def async_unlock(self, **kwargs):
        """Unlock the car."""
        await self.instrument.unlock()
        self.notify_updated()
