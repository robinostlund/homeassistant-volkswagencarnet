"""
Support for Volkswagen Carnet Platform
"""
import logging

from homeassistant.components.lock import LockDevice
from custom_components.volkswagencarnet import VolkswagenEntity


_LOGGER = logging.getLogger(__name__)

# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Volvo On Call lock."""
    if discovery_info is None:
        return

    add_devices([VolkswagenLock(hass, *discovery_info)])

class VolkswagenLock(VolkswagenEntity, LockDevice):
    """Represents a car lock."""

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        _LOGGER.debug('Getting state of %s lock' % self._attribute)
        return self.vehicle.is_doors_locked
