# -*- coding: utf-8 -*-
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from volkswagencarnet import Connection, Vehicle

from .const import (
    COMPONENTS,
    CONF_MUTABLE,
    CONF_REGION,
    CONF_REPORT_REQUEST,
    CONF_REPORT_SCAN_INTERVAL,
    CONF_SCANDINAVIAN_MILES,
    CONF_SPIN,
    CONF_VEHICLE,
    DATA,
    DATA_KEY,
    DEFAULT_REGION,
    DEFAULT_REPORT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
    RESOURCES_DICT,
    SIGNAL_STATE_UPDATED,
    UNDO_UPDATE_LISTENER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Setup Volkswagen WeConnect component"""

    if entry.options.get(CONF_SCAN_INTERVAL):
        update_interval = timedelta(minutes=entry.options[CONF_SCAN_INTERVAL])
    else:
        update_interval = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

    coordinator = VolkswagenCoordinator(hass, entry, update_interval)
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    data = VolkswagenData(entry.data, coordinator)
    instruments = coordinator.data

    def is_enabled(attr):
        """Return true if the user has enabled the resource."""
        return attr in entry.data.get(CONF_RESOURCES, [attr])

    components = set()
    for instrument in (
        instrument
        for instrument in instruments
        if instrument.component in COMPONENTS and is_enabled(instrument.slug_attr)
    ):
        data.instruments.add(instrument)
        components.add(COMPONENTS[instrument.component])

    for component in components:
        coordinator.platforms.append(component)
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA: data,
        UNDO_UPDATE_LISTENER: entry.add_update_listener(_async_update_listener),
    }

    return True


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Plaato component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    return await async_unload_coordinator(hass, entry)


async def async_unload_coordinator(hass: HomeAssistant, entry: ConfigEntry):
    """Unload auth token based entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA].coordinator
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in COMPONENTS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class VolkswagenData:
    """Hold component state."""

    def __init__(self, config, coordinator=None):
        """Initialize the component state."""
        self.vehicles = set()
        self.instruments = set()
        self.config = config.get(DOMAIN, config)
        self.names = self.config.get(CONF_NAME, None)
        self.coordinator = coordinator

    def instrument(self, vin, component, attr):
        """Return corresponding instrument."""
        return next(
            (
                instrument
                for instrument in (
                    self.coordinator.data
                    if self.coordinator is not None
                    else self.instruments
                )
                if instrument.vehicle.vin == vin
                and instrument.component == component
                and instrument.attr == attr
            ),
            None,
        )

    def vehicle_name(self, vehicle):
        """Provide a friendly name for a vehicle."""
        if isinstance(self.names, str):
            return self.names

        if vehicle.vin and vehicle.vin.lower() in self.names:
            return self.names[vehicle.vin.lower()]
        elif vehicle.vin:
            return vehicle.vin
        else:
            return ""


class VolkswagenEntity(Entity):
    """Base class for all Volkswagen entities."""

    def __init__(self, data, vin, component, attribute):
        """Initialize the entity."""
        self.data = data
        self.vin = vin
        self.component = component
        self.attribute = attribute
        self.coordinator = data.coordinator

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """

        # Ignore manual update requests if the entity is disabled
        if not self.enabled:
            return

        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Register update dispatcher."""
        if self.coordinator is not None:
            self.async_on_remove(
                self.coordinator.async_add_listener(self.async_write_ha_state)
            )
        else:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass, SIGNAL_STATE_UPDATED, self.async_write_ha_state
                )
            )

    @property
    def instrument(self):
        """Return corresponding instrument."""
        return self.data.instrument(self.vin, self.component, self.attribute)

    @property
    def icon(self):
        """Return the icon."""
        if self.instrument.attr in ["battery_level", "charging"]:
            return icon_for_battery_level(
                battery_level=self.instrument.state, charging=self.vehicle.charging
            )
        else:
            return self.instrument.icon

    @property
    def vehicle(self):
        """Return vehicle."""
        return self.instrument.vehicle

    @property
    def _entity_name(self):
        return self.instrument.name

    @property
    def _vehicle_name(self):
        return self.data.vehicle_name(self.vehicle)

    @property
    def name(self):
        """Return full name of the entity."""
        return f"{self._vehicle_name} {self._entity_name}"

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        attributes = dict(
            self.instrument.attributes,
            model=f"{self.vehicle.model}/{self.vehicle.model_year}",
        )

        if not self.vehicle.is_model_image_supported:
            return attributes

        attributes["image_url"] = self.vehicle.model_image
        return attributes

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self.vin)},
            "name": self._vehicle_name,
            "manufacturer": "Volkswagen",
            "model": self.vehicle.model,
            "sw_version": self.vehicle.model_year,
        }

    @property
    def available(self):
        """Return if sensor is available."""
        if self.data.coordinator is not None:
            return self.data.coordinator.last_update_success
        return True

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.vin}-{self.component}-{self.attribute}"


class VolkswagenCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, entry, update_interval: timedelta):
        self.vin = entry.data[CONF_VEHICLE]
        self.entry = entry
        self.platforms = []
        self.report_last_updated = None

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Update data via library."""
        self.connection = Connection(
            session=async_get_clientsession(self.hass),
            username=self.entry.data[CONF_USERNAME],
            password=self.entry.data[CONF_PASSWORD],
        )

        vehicle = await self.update()

        if not vehicle:
            _LOGGER.warning("Could not query update from volkswagen WeConnect")
            raise Exception

        if self.entry.options.get(CONF_REPORT_REQUEST, False):
            await self.report_request(vehicle)

        dashboard = vehicle.dashboard(
            mutable=self.entry.data.get(CONF_MUTABLE),
            spin=self.entry.data.get(CONF_SPIN),
            scandinavian_miles=self.entry.data.get(CONF_SCANDINAVIAN_MILES),
        )

        return dashboard.instruments

    async def update(self) -> Union[bool, Vehicle]:
        """Update status from Volkswagen WeConnect"""

        # check if we can login
        if not self.connection.logged_in:
            await self.connection._login()
            if not self.connection.logged_in:
                _LOGGER.warning(
                    "Could not login to volkswagen WeConnect, please check your credentials and verify that the service is working"
                )
                return False

        # update vehicles
        if not await self.connection.update():
            _LOGGER.warning("Could not query update from volkswagen WeConnect")
            return False

        _LOGGER.debug("Updating data from volkswagen WeConnect")
        for vehicle in self.connection.vehicles:
            if vehicle.vin == self.vin:
                return vehicle

        return False

    async def report_request(self, vehicle: Vehicle):
        """Request car to report itself an update to Volkswagen WeConnect"""
        report_interval = self.entry.options.get(
            CONF_REPORT_SCAN_INTERVAL, DEFAULT_REPORT_UPDATE_INTERVAL
        )

        if not self.report_last_updated:
            days_since_last_update = 1
        else:
            days_since_last_update = (datetime.now() - self.report_last_updated).days

        if days_since_last_update < report_interval:
            return

        try:
            # check if we can login
            if not self.connection.logged_in:
                await self.connection._login()
                if not self.connection.logged_in:
                    _LOGGER.warning(
                        "Could not login to volkswagen WeConnect, please check your credentials and verify that the service is working"
                    )
                    return

            # request report
            if not await vehicle.request_report():
                _LOGGER.warning("Could not request report from volkswagen WeConnect")
                return

            self.report_last_updated = datetime.now()
        except:
            # This is actually not critical so...
            pass
