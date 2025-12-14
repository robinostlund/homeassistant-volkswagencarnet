"""Volkswagen Connect custom integration for Home Assistant."""

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

# pylint: disable=no-name-in-module,hass-relative-import
from volkswagencarnet.vw_connection import Connection
from volkswagencarnet.vw_dashboard import (
    BinarySensor,
    DoorLock,
    Instrument,
    Climate,
    Number,
    Position,
    Select,
    Sensor,
    Switch,
    TrunkLock,
)
from volkswagencarnet.vw_vehicle import Vehicle

from .const import (
    COMPONENTS,
    CONF_AVAILABLE_RESOURCES,
    CONF_CONVERT,
    CONF_IMPERIAL_UNITS,
    CONF_MUTABLE,
    CONF_NO_CONVERSION,
    CONF_REGION,
    CONF_SCANDINAVIAN_MILES,
    CONF_SPIN,
    CONF_VEHICLE,
    DATA,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SIGNAL_STATE_UPDATED,
    UNDO_UPDATE_LISTENER,
    UPDATE_CALLBACK,
)
from .util import get_convert_conf

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Perform Volkswagen Connect component setup."""

    scan_interval_conf = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    )
    update_interval = timedelta(minutes=scan_interval_conf)

    coordinator = VolkswagenCoordinator(hass, entry, update_interval)
    coordinator.async_add_listener(coordinator.async_update_listener)

    # Sync volkswagencarnet library log level with integration log level
    volkswagencarnet_logger = logging.getLogger("volkswagencarnet")
    if _LOGGER.isEnabledFor(logging.DEBUG):
        volkswagencarnet_logger.setLevel(logging.DEBUG)
        _LOGGER.debug("Enabled DEBUG logging for volkswagencarnet library")
    else:
        volkswagencarnet_logger.setLevel(logging.INFO)

    if not await coordinator.async_login():
        _LOGGER.warning("Failed to login, triggering reauth")
        entry.async_start_reauth(hass)
        return False

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, coordinator.async_logout)

    # First refresh with retry on errors
    await coordinator.async_config_entry_first_refresh()

    data: VolkswagenData = VolkswagenData(entry.data, coordinator)
    instruments = coordinator.data

    def is_enabled(attr: str) -> bool:
        """Return true if the user has enabled the resource."""
        return attr in entry.options.get(CONF_RESOURCES, [attr])

    def is_new(attr: str) -> bool:
        """Return true if the resource is new."""
        return attr not in entry.options.get(CONF_AVAILABLE_RESOURCES, [attr])

    components: set[str] = set()
    for instrument in (instr for instr in instruments if instr.component in COMPONENTS):
        # Add resource if enabled or new
        if is_enabled(instrument.slug_attr) or (
            is_new(instrument.slug_attr) and not entry.pref_disable_new_entities
        ):
            data.instruments.add(instrument)
            components.add(COMPONENTS[instrument.component])

    hass.data[DOMAIN][entry.entry_id] = {
        UPDATE_CALLBACK: update_callback,
        DATA: data,
        UNDO_UPDATE_LISTENER: entry.add_update_listener(_async_update_listener),
    }

    coordinator.platforms.extend(components)
    await hass.config_entries.async_forward_entry_setups(entry, components)

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    version = entry.version

    _LOGGER.debug("Migrating config from version %s", version)

    # 1 -> 2: Move resources from data -> options
    if version == 1:
        default_convert_conf = get_convert_conf(entry)
        version = entry.version = 2
        options = dict(entry.options)
        data = dict(entry.data)

        options[CONF_RESOURCES] = data[CONF_RESOURCES]
        options[CONF_CONVERT] = options.get(CONF_CONVERT, default_convert_conf)
        data.pop(CONF_RESOURCES, None)

        hass.config_entries.async_update_entry(entry, data=data, options=options)

    # 2 -> 3: Fix empty "convert" option
    if version == 2:
        version = entry.version = 3
        options = dict(entry.options)
        options.pop(CONF_CONVERT, None)
        data = dict(entry.data)

        hass.config_entries.async_update_entry(entry, data=data, options=options)

    _LOGGER.info("Migration to config version %s successful", version)
    return True


def update_callback(hass: HomeAssistant, coordinator: DataUpdateCoordinator) -> None:
    """Request data update."""
    _LOGGER.debug("Update request callback")
    hass.async_create_task(coordinator.async_request_refresh())


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Removing update listener")
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    return await async_unload_coordinator(hass, entry)


async def async_unload_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload coordinator based entry."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator: VolkswagenCoordinator | None = data.coordinator

    if coordinator is None:
        _LOGGER.error("Coordinator not found during unload")
        return False

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


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class VolkswagenData:
    """Hold component state."""

    def __init__(
        self, config: dict[str, Any], coordinator: "VolkswagenCoordinator | None" = None
    ) -> None:
        """Initialize the component state."""
        self.vehicles: set[Vehicle] = set()
        self.instruments: set[Instrument] = set()
        self.config: dict[str, object] = config.get(DOMAIN, config)
        self.names: str = self.config.get(CONF_NAME, "")
        self.coordinator: VolkswagenCoordinator | None = coordinator

    def instrument(self, vin: str, component: str, attr: str) -> Instrument:
        """Return corresponding instrument."""
        instruments = (
            self.coordinator.data if self.coordinator is not None else self.instruments
        )

        instrument = next(
            (
                instr
                for instr in instruments
                if instr.vehicle.vin == vin
                and instr.component == component
                and instr.attr == attr
            ),
            None,
        )

        if instrument is None:
            raise ValueError(
                f"Instrument not found; component: {component}, attribute: {attr}, vin: {vin}"
            )

        return instrument

    def vehicle_name(self, vehicle: Vehicle) -> str:
        """Provide a friendly name for a vehicle.

        Prefer the configured name from entry data, then options,
        then VIN, then 'Unknown Vehicle'.
        """
        # Priority 1: Config entry data (set during initial setup)
        if self.coordinator is not None:
            entry = getattr(self.coordinator, "entry", None)
            if entry:
                # Try data first (initial setup stores name here)
                name_from_data = entry.data.get(CONF_NAME)
                if name_from_data:
                    return name_from_data

                # Then try options (if user updates it later)
                name_from_options = entry.options.get(CONF_NAME)
                if name_from_options:
                    return name_from_options

        # Priority 2: Fallback to self.names (legacy)
        if isinstance(self.names, str) and self.names:
            return self.names

        # Priority 3: VIN
        if vehicle.vin:
            return vehicle.vin

        return "Unknown Vehicle"


class VolkswagenEntity(CoordinatorEntity, RestoreEntity):
    """Base class for all Volkswagen entities."""

    last_updated: datetime | None = None
    restored_state: State | None = None

    def __init__(
        self,
        data: VolkswagenData,
        vin: str,
        component: str,
        attribute: str,
        callback=None,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Initialize the entity."""
        super().__init__(data.coordinator)

        self.data: VolkswagenData = data
        self.vin: str = vin
        self.component: str = component
        self.attribute: str = attribute
        self.coordinator: VolkswagenCoordinator | None = data.coordinator
        self.callback = callback

        # Set instrument callback for updates
        def update_callbacks() -> None:
            if callback is not None:
                callback(self.hass, data.coordinator)

        self.instrument.callback = update_callbacks

    @callback
    def async_write_ha_state(self) -> None:
        """Write state to HA, but only if needed."""
        try:
            backend_refresh_time = self.instrument.last_refresh
        except ValueError:
            # Instrument not found - mark as unavailable
            _LOGGER.debug(
                "Instrument not found for entity %s, marking as unavailable",
                self.entity_id,
            )
            super().async_write_ha_state()
            return
        # Get the previous state from the state machine if found
        prev: State | None = self.hass.states.get(self.entity_id)

        # Need to persist state if:
        # - There is no previous state
        # - The backend refresh time has changed
        # - The state value has changed (string conversion for type compatibility)
        if prev is None:
            super().async_write_ha_state()
            return

        state_changed = str(self.state or STATE_UNKNOWN) != str(prev.state)
        time_changed = str(prev.attributes.get("last_updated", None)) != str(
            backend_refresh_time
        )

        if time_changed or state_changed:
            super().async_write_ha_state()
        else:
            _LOGGER.debug(
                "%s: state unchanged ('%s' == '%s'), skipping update",
                self.name,
                prev.state,
                self.state,
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity via manual update service."""
        if not self.enabled:
            _LOGGER.debug("Entity %s is disabled, skipping update", self.name)
            return

        if self.coordinator is not None:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Coordinator not set for entity %s", self.name)

    async def async_added_to_hass(self) -> None:
        """Register update dispatcher when entity is added to HA."""
        self.restored_state = await self.async_get_last_state()

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
    def instrument(
        self,
    ) -> (
        BinarySensor
        | Climate
        | DoorLock
        | Position
        | Select
        | Sensor
        | Switch
        | TrunkLock
        | Number
        | Instrument
    ):
        """Return corresponding instrument."""
        return self.data.instrument(self.vin, self.component, self.attribute)

    @property
    def icon(self) -> str | None:
        """Return the icon."""
        if self.instrument.attr in ("battery_level", "charging"):
            return icon_for_battery_level(
                battery_level=self.instrument.state,
                charging=self.vehicle.charging,
            )
        return self.instrument.icon

    @property
    def vehicle(self) -> Vehicle:
        """Return vehicle."""
        return self.instrument.vehicle

    @property
    def _entity_name(self) -> str:
        """Return entity name."""
        return self.instrument.name

    @property
    def _vehicle_name(self) -> str:
        """Return vehicle name."""
        return self.data.vehicle_name(self.vehicle)

    @property
    def name(self) -> str:
        """Return full name of the entity."""
        return self._entity_name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def assumed_state(self) -> bool:
        """Return true if unable to access real state of entity."""
        return getattr(self.instrument, "assumed_state", True)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        attributes: dict[str, Any] = {
            **self.instrument.attributes,
            "model": f"{self.vehicle.model}/{self.vehicle.model_year}",
            "vin": self.vin,
            "last_updated": self.instrument.last_refresh,
        }

        if self.vehicle.is_model_image_supported:
            attributes["image_url"] = self.vehicle.model_image

        return attributes

    @property
    def device_info(self) -> dict[str, object]:
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self.vin)},
            "name": self._vehicle_name,
            "manufacturer": "Volkswagen",
            "model": self.vehicle.model,
            "sw_version": self.vehicle.model_year,
            "serial_number": self.vin,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        try:
            # Check if instrument exists
            _ = self.instrument
            return (
                super().available
                and self.coordinator.last_update_success
                and self.instrument is not None
            )
        except ValueError:
            # Instrument not found (disabled or not supported)
            return False

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.vin}-{self.component}-{self.attribute}"

    def notify_updated(self) -> None:
        """Schedule entity updates."""
        if self.coordinator is not None:
            self.hass.add_job(self.coordinator.async_request_refresh)
        else:
            _LOGGER.warning("Cannot notify update: coordinator not set")


class VolkswagenCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, update_interval: timedelta
    ) -> None:
        """Initialize the coordinator."""
        self.vin = entry.data[CONF_VEHICLE].upper()
        self.entry = entry
        self.platforms: list[str] = []
        self.connection = Connection(
            session=async_get_clientsession(hass),
            username=self.entry.data[CONF_USERNAME],
            password=self.entry.data[CONF_PASSWORD],
            country=self.entry.options.get(CONF_REGION, self.entry.data[CONF_REGION]),
        )

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    def async_update_listener(self) -> None:
        """Listen for update events."""
        _LOGGER.debug(
            "Async update finished for %s (%s). Next update in %s",
            self.vin,
            self.name,
            self.update_interval,
        )

    async def _async_update_data(self) -> list[Instrument]:
        """Update data via library."""
        vehicle = await self.update()

        if vehicle is None:
            self.entry.async_start_reauth(self.hass)
            raise ConfigEntryAuthFailed(
                "Failed to update Volkswagen Connect. Need to accept EULA? "
                "Try logging in to the portal: https://www.myvolkswagen.net/"
            )

        convert_conf = self.entry.options.get(
            CONF_CONVERT, self.entry.data.get(CONF_CONVERT, CONF_NO_CONVERSION)
        )

        dashboard = vehicle.dashboard(
            mutable=self.entry.data.get(CONF_MUTABLE),
            spin=self.entry.data.get(CONF_SPIN),
            miles=convert_conf == CONF_IMPERIAL_UNITS,
            scandinavian_miles=convert_conf == CONF_SCANDINAVIAN_MILES,
        )

        return dashboard.instruments

    async def async_logout(self, event: Event | None = None) -> bool:
        """Logout from Volkswagen Connect."""
        if event is not None:
            _LOGGER.debug("Logging out due to event: %s", event.event_type)

        try:
            if self.connection.logged_in:
                await self.connection.logout()
                _LOGGER.debug("Successfully logged out")
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Could not log out from Volkswagen Connect: %s", err)
            return False

        return True

    async def async_login(self) -> bool:
        """Login to Volkswagen Connect."""
        if self.connection.logged_in:
            _LOGGER.debug("Already logged in")
            return True

        try:
            await self.connection.doLogin(3)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Login failed: %s", err)
            return False

        if not self.connection.logged_in:
            _LOGGER.warning(
                "Could not login to Volkswagen Connect. "
                "Please check your credentials and verify that the service is working. "
                "You may need to accept the EULA at https://www.myvolkswagen.net/"
            )
            return False

        _LOGGER.debug("Successfully logged in to Volkswagen Connect")
        return True

    async def update(self) -> Vehicle | None:
        """Update status from Volkswagen Connect."""
        try:
            if not await self.connection.update():
                _LOGGER.warning("Could not query update from Volkswagen Connect")
                return None

            _LOGGER.debug("Updating data from Volkswagen Connect")

            for vehicle in self.connection.vehicles:
                if vehicle.vin.upper() == self.vin:
                    return vehicle

            _LOGGER.warning("Vehicle with VIN %s not found in connection", self.vin)
            return None
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Error during update: %s", err)
            return None
