"""Services exposed to Home Assistant."""

import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .util import get_coordinator_by_device_id, get_vehicle, validate_charge_max_current

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_CHARGER_MAX_CURRENT_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Optional("max_current"): vol.In([5, 10, 13, 16, 32, "5", "10", "13", "16", "32", "reduced", "max"]),
    },
    extra=vol.ALLOW_EXTRA,  # FIXME, should not be needed
)


class ChargerService:
    """Charger services class."""

    def __init__(self, hass: HomeAssistant):
        """Init."""
        self.hass: HomeAssistant = hass

    async def set_charger_max_current(self, service_call: ServiceCall) -> bool:
        """Service for setting max charging current."""
        c = await get_coordinator_by_device_id(self.hass, service_call.data.get("device_id"))
        v = get_vehicle(c)

        # parse service call
        level = validate_charge_max_current(service_call.data.get("max_current", None))

        if level is None:
            raise ValueError("Can't change value to None")

        # Apply
        res = await v.set_charger_current(level)
        self.hass.add_job(c.async_request_refresh)
        return res
