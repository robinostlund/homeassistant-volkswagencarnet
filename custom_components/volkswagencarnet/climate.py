"""Climate support for Volkswagen WeConnect Platform."""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)

from . import VolkswagenEntity, VolkswagenData
from .const import DATA_KEY, DATA, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Perform climate platform setup."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenClimate(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    """Perform climate device setup."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenClimate(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
                callback=hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (instrument for instrument in data.instruments if instrument.component == "climate")
        )

    return True


class VolkswagenClimate(VolkswagenEntity, ClimateEntity):
    """Representation of a Volkswagen WeConnect Climate."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_hvac_mode = HVACMode.HEAT_COOL
    _attr_min_temp = 15.5
    _attr_max_temp = 30
    _enable_turn_on_off_backwards_compatibility = False  # Remove after HA version 2025.1

    def __init__(self, data: VolkswagenData, vin: str, component: str, attribute: str, callback=None):
        """Initialize switch."""
        super().__init__(data, vin, component, attribute, callback)
        self._update_state()

    def _update_state(self) -> None:
        self._attr_target_temperature = float(self.instrument.target_temperature)
        if self.instrument.hvac_mode is True:
            self._attr_hvac_mode = HVACMode.HEAT_COOL
        else:
            self._attr_hvac_mode = HVACMode.OFF

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT_COOL)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        _LOGGER.debug("Setting temperature for: %s", self.instrument.attr)
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature:
            await self.instrument.set_temperature(temperature)
            self._update_state()
            self.notify_updated()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug("Setting mode for: %s", self.instrument.attr)
        if hvac_mode == HVACMode.OFF:
            await self.instrument.set_hvac_mode(False)
        elif hvac_mode == HVACMode.HEAT_COOL:
            await self.instrument.set_hvac_mode(True)
        self._update_state()
        self.notify_updated()
