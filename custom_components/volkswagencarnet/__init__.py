"""Volkswagen Connect custom integration for Home Assistant."""

import asyncio
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
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
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

# pylint: disable=no-name-in-module,hass-relative-import
from volkswagencarnet.vw_connection import Connection
from volkswagencarnet.vw_dashboard import (
    BinarySensor,
    DoorLock,
    Instrument,
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
    CONF_DEBUG,
    CONF_IMPERIAL_UNITS,
    CONF_MUTABLE,
    CONF_NO_CONVERSION,
    CONF_REGION,
    CONF_SCANDINAVIAN_MILES,
    CONF_SPIN,
    CONF_VEHICLE,
    DATA,
    DEFAULT_DEBUG,
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

    if not await coordinator.async_login():
        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH},
            data=entry,
        )
        return False

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, coordinator.async_logout)

    # First refresh, with retry on errors
    await coordinator.async_config_entry_first_refresh()

    data: VolkswagenData = VolkswagenData(entry.data, coordinator)
    instruments = coordinator.data

    def is_enabled(attr):
        """Return true if the user has enabled the resource."""
        return attr in entry.options.get(CONF_RESOURCES, [attr])

    def is_new(attr):
        """Return true if the resource is new."""
        return attr not in entry.options.get(CONF_AVAILABLE_RESOURCES, [attr])

    components = set()
    for instrument in (
        instrument for instrument in instruments if instrument.component in COMPONENTS
    ):
        # Add resource if it's enabled or new
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
        # Backward compatibility
        default_convert_conf = get_convert_conf(entry)

        version = entry.version = 2
        options = dict(entry.options)
        data = dict(entry.data)
        options[CONF_RESOURCES] = data[CONF_RESOURCES]
        options[CONF_CONVERT] = options.get(CONF_CONVERT, default_convert_conf)
        data.pop(CONF_RESOURCES, None)

        hass.config_entries.async_update_entry(entry, data=data, options=options)
    if version == 2:
        # Fix the empty added "convert" option that breaks further conversion configuration
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Removing update listener")
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    return await async_unload_coordinator(hass, entry)


async def async_unload_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle options update."""
    return await hass.config_entries.async_reload(entry.entry_id)


class VolkswagenData:
    """Hold component state."""

    def __init__(
        self, config: dict, coordinator: DataUpdateCoordinator | None = None
    ) -> None:
        """Initialize the component state."""
        self.vehicles: set[Vehicle] = set()
        self.instruments: set[Instrument] = set()
        self.config: dict[str, object] = config.get(DOMAIN, config)
        self.names: str = self.config.get(CONF_NAME, "")
        self.coordinator: VolkswagenCoordinator | None = coordinator

    def instrument(self, vin: str, component: str, attr: str) -> Instrument:
        """Return corresponding instrument."""
        ret = next(
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
        if ret is None:
            raise ValueError(
                f"Instrument not found; component: {component}, attribute: {attr}"
            )
        return ret

    def vehicle_name(self, vehicle: Vehicle) -> str:
        """Provide a friendly name for a vehicle."""
        if isinstance(self.names, str):
            return self.names

        if vehicle.vin:
            return vehicle.vin
        return ""


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
        # Pass coordinator to CoordinatorEntity.
        super().__init__(data.coordinator)

        def update_callbacks() -> None:
            if callback is not None:
                callback(self.hass, data.coordinator)

        self.data: VolkswagenData = data
        self.vin: str = vin
        self.component: str = component
        self.attribute: str = attribute
        self.coordinator: VolkswagenCoordinator | None = data.coordinator
        self.instrument.callback = update_callbacks
        self.callback = callback

    @callback
    def async_write_ha_state(self) -> None:
        """Write state to HA, but only if needed."""
        backend_refresh_time = self.instrument.last_refresh
        # Get the previous state from the state machine if found
        prev: State | None = self.hass.states.get(self.entity_id)

        # need to persist state if:
        # - there is no previous state
        # - there is no information about when the last backend update was done
        # - the state has changed (need to do string conversion here, as "new" state might be numeric,
        #   but the stored one is a string... sigh)
        if (
            prev is None
            or str(prev.attributes.get("last_updated", None))
            != str(backend_refresh_time)
            or str(self.state or STATE_UNKNOWN) != str(prev.state)
        ):
            super().async_write_ha_state()
        else:
            _LOGGER.debug(
                "%s: state not changed ('%s' == '%s'), skipping update",
                self.name,
                prev.state,
                self.state,
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator (push updates)."""
        raise NotImplementedError("Implement in subclasses.")

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        # Ignore manual update requests if the entity is disabled
        if not self.enabled:
            return
        if self.coordinator is not None:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Coordinator not set")

    # pylint: disable-next=hass-missing-super-call
    async def async_added_to_hass(self) -> None:
        """Register update dispatcher."""
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
        if self.instrument.attr in ["battery_level", "charging"]:
            return icon_for_battery_level(
                battery_level=self.instrument.state, charging=self.vehicle.charging
            )
        return self.instrument.icon

    @property
    def vehicle(self) -> Vehicle:
        """Return vehicle."""
        return self.instrument.vehicle

    @property
    def _entity_name(self) -> str:
        return self.instrument.name

    @property
    def _vehicle_name(self) -> str:
        return self.data.vehicle_name(self.vehicle)

    @property
    def name(self) -> str:
        """Return full name of the entity."""
        return f"{self._vehicle_name} {self._entity_name}"

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def assumed_state(self) -> bool:
        """Return true if unable to access real state of entity."""
        if hasattr(self.instrument, "assumed_state"):
            return self.instrument.assumed_state
        return True

    @property
    def extra_state_attributes(self) -> dict:
        """Return device specific state attributes."""
        attributes = dict(
            self.instrument.attributes,
            model=f"{self.vehicle.model}/{self.vehicle.model_year}",
            last_updated=self.instrument.last_refresh,
        )

        if not self.vehicle.is_model_image_supported:
            return attributes

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
        """Return if sensor is available."""
        if self.data.coordinator is not None:
            return self.data.coordinator.last_update_success
        return True

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.vin}-{self.component}-{self.attribute}"

    def notify_updated(self):
        """Schedule entity updates."""
        self.hass.add_job(self.coordinator.async_request_refresh)


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
            fulldebug=self.entry.options.get(
                CONF_DEBUG, self.entry.data.get(CONF_DEBUG, DEFAULT_DEBUG)
            ),
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
            raise UpdateFailed(
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

    async def async_logout(self, event: Event = None) -> bool:
        """Logout from Volkswagen Connect."""
        if event is not None:
            _LOGGER.debug("Logging out due to event %s", event.event_type)
        try:
            if self.connection.logged_in:
                await self.connection.logout()
        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Could not log out from Volkswagen Connect, %s", ex)
            return False
        return True

    async def async_login(self) -> bool:
        """Login to Volkswagen Connect."""
        # check if we can login
        if not self.connection.logged_in:
            await self.connection.doLogin(3)
            if not self.connection.logged_in:
                _LOGGER.warning(
                    "Could not login to Volkswagen Connect, "
                    "please check your credentials and verify that "
                    "the service is working"
                )
                return False

        return True

    async def update(self) -> Vehicle | None:
        """Update status from Volkswagen Connect."""
        # update vehicles
        if not await self.connection.update():
            _LOGGER.warning("Could not query update from Volkswagen Connect")
            return None

        _LOGGER.debug("Updating data from Volkswagen Connect")
        for vehicle in self.connection.vehicles:
            if vehicle.vin.upper() == self.vin:
                return vehicle

        return None
