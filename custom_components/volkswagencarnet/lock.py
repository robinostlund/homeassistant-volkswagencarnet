"""
Support for Volkswagen Carnet Platform
"""
import logging
from homeassistant.components.lock import LockEntity
from . import VolkswagenEntity, DATA_KEY

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Setup the volkswagen lock """
    if discovery_info is None:
        return

    async_add_entities([VolkswagenLock(hass.data[DATA_KEY], *discovery_info)])

class VolkswagenLock(VolkswagenEntity, LockEntity):
    """Represents a Volkswagen Carnet Lock."""

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        _LOGGER.debug('Getting state of %s' % self.instrument.attr)
        return self.instrument.is_locked

    async def async_lock(self, **kwargs):
        """Lock the car."""
        await self.instrument.lock()

    async def async_unlock(self, **kwargs):
        """Unlock the car."""
        await self.instrument.unlock()