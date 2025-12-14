"""Climate support for Volkswagen Connect Platform."""

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from . import VolkswagenData, VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

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
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "climate"
            )
        )

    return True


class VolkswagenClimate(VolkswagenEntity, ClimateEntity):
    """Representation of a Volkswagen WeConnect Climate."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_min_temp = 15.5
    _attr_max_temp = 30
    _attr_translation_key = "climate"
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        data: VolkswagenData,
        vin: str,
        component: str,
        attribute: str,
        callback=None,
    ) -> None:
        """Initialize climate entity."""
        super().__init__(data, vin, component, attribute, callback)

    @property
    def should_poll(self) -> bool:
        """Return False as entity is updated by coordinator."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.last_update_success
            and self.instrument is not None
        )

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        try:
            return float(self.instrument.target_temperature)
        except (ValueError, TypeError, AttributeError):
            _LOGGER.debug("Could not get target temperature for %s", self.name)
            return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation mode."""
        try:
            if self.instrument.hvac_mode is True:
                return HVACMode.HEAT_COOL
        except AttributeError:
            _LOGGER.debug("Could not get HVAC mode for %s", self.name)
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if hasattr(self.instrument, "current_temperature"):
            try:
                return float(self.instrument.current_temperature)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self.hvac_mode == HVACMode.OFF:
            return "mdi:hvac-off"
        return "mdi:hvac"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        # Check if vehicle is available
        if not hasattr(self.instrument, "vehicle"):
            return attrs

        vehicle = self.instrument.vehicle

        # Add climatisation without external power status
        if vehicle.is_climatisation_without_external_power_supported:
            attrs["climatisation_without_external_power"] = (
                vehicle.climatisation_without_external_power
            )

        # Add remaining climatisation time (for electric climatisation)
        if vehicle.is_electric_remaining_climatisation_time_supported:
            attrs["remaining_time_minutes"] = (
                vehicle.electric_remaining_climatisation_time
            )

        # Add window heating status
        if vehicle.is_window_heater_supported:
            attrs["window_heating"] = vehicle.window_heater

        # For combustion climatisation, show heating duration
        if hasattr(self.instrument, "duration"):
            attrs["heating_duration_minutes"] = self.instrument.duration

        # Add auxiliary remaining time (for combustion/auxiliary climatisation)
        if vehicle.is_auxiliary_remaining_climatisation_time_supported:
            attrs["auxiliary_remaining_time_minutes"] = (
                vehicle.auxiliary_remaining_climatisation_time
            )

        return attrs

    async def async_turn_off(self) -> None:
        """Turn off climate control."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        """Turn on climate control."""
        await self.async_set_hvac_mode(HVACMode.HEAT_COOL)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)

        if temperature is None:
            _LOGGER.warning("No temperature provided for %s", self.name)
            return

        # Validate temperature range
        if not self._attr_min_temp <= temperature <= self._attr_max_temp:
            _LOGGER.error(
                "Temperature %s out of range (%s-%s) for %s",
                temperature,
                self._attr_min_temp,
                self._attr_max_temp,
                self.name,
            )
            return

        try:
            _LOGGER.debug(
                "Setting temperature to %s°C for %s (VIN: %s)",
                temperature,
                self.name,
                self.vin,
            )
            await self.instrument.set_temperature(temperature)

            # Optimistically update state for immediate UI feedback
            self.async_write_ha_state()

            # Request coordinator refresh to get confirmed state from API
            await self.coordinator.async_request_refresh()

        except Exception as error:
            _LOGGER.error(
                "Failed to set temperature for %s: %s",
                self.name,
                error,
                exc_info=True,
            )
            # Re-trigger state update to revert optimistic change
            self.async_write_ha_state()
            raise

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        try:
            _LOGGER.debug(
                "Setting HVAC mode to %s for %s (VIN: %s)",
                hvac_mode,
                self.name,
                self.vin,
            )

            if hvac_mode == HVACMode.OFF:
                await self.instrument.set_hvac_mode(False)
            elif hvac_mode == HVACMode.HEAT_COOL:
                await self.instrument.set_hvac_mode(True)
            else:
                _LOGGER.warning("Unsupported HVAC mode %s for %s", hvac_mode, self.name)
                return

            # Request coordinator refresh to get updated state
            await self.coordinator.async_request_refresh()

        except Exception as error:
            _LOGGER.error(
                "Failed to set HVAC mode for %s: %s",
                self.name,
                error,
                exc_info=True,
            )
            raise
