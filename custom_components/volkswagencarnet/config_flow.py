"""Config flow for Volkswagen Connect integration."""

import asyncio
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import async_get

# pylint: disable=no-name-in-module,hass-relative-import
from volkswagencarnet.vw_connection import Connection
from volkswagencarnet.vw_vehicle import Vehicle

from .const import (
    CONF_AVAILABLE_RESOURCES,
    CONF_CONVERT,
    CONF_MUTABLE,
    CONF_NO_CONVERSION,
    CONF_REGION,
    CONF_SPIN,
    CONF_VEHICLE,
    CONVERT_DICT,
    DEFAULT_REGION,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .util import get_coordinator, get_vehicle

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=""): str,
        vol.Required(CONF_USERNAME, default=""): str,
        vol.Required(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_SPIN, default=""): str,
        vol.Optional(CONF_REGION, default=DEFAULT_REGION): str,
        vol.Optional(CONF_MUTABLE, default=True): cv.boolean,
        vol.Optional(CONF_CONVERT, default=CONF_NO_CONVERSION): vol.In(CONVERT_DICT),
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): cv.positive_int,
    }
)


class VolkswagenCarnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow for Volkswagen Connect."""

    VERSION = 3

    def __init__(self) -> None:
        """Initialize config flow."""
        self._entry: ConfigEntry | None = None
        self._init_info: dict = {}
        self._errors: dict[str, str] = {}
        self._connection: Connection | None = None
        self.task_login: asyncio.Task | None = None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle user step."""
        if user_input is not None:
            self._errors = {}
            self._init_info = user_input
            self.task_login = None

            _LOGGER.debug("Creating connection to Volkswagen Connect")
            self._connection = Connection(
                session=async_get_clientsession(self.hass),
                username=self._init_info[CONF_USERNAME],
                password=self._init_info[CONF_PASSWORD],
                country=self._init_info[CONF_REGION],
            )

            return await self.async_step_login()

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=self._errors,
        )

    async def _async_task_login(self) -> None:
        """Handle login task."""
        try:
            assert self._connection is not None
            await self._connection.doLogin()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Failed to login due to error: %s", err)
            self._errors["base"] = "cannot_connect"
            return

        if not self._connection.logged_in:
            self._errors["base"] = "cannot_connect"
            return

        self.hass.async_create_task(
            self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
        )

    async def async_step_login(self, user_input: dict | None = None) -> FlowResult:
        """Handle login step."""
        if not self.task_login:
            self.task_login = self.hass.async_create_task(self._async_task_login())

            return self.async_show_progress(
                step_id="login",
                progress_action="task_login",
                progress_task=self.task_login,
            )

        try:
            await self.task_login
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Login task failed: %s", err)
            return self.async_abort(reason="cannot_connect")

        if self._errors:
            return self.async_show_progress_done(next_step_id="user")

        assert self._connection is not None
        for vehicle in self._connection.vehicles:
            _LOGGER.info("Found vehicle with VIN: %s", vehicle.vin)

        self._init_info["CONF_VEHICLES"] = {
            vehicle.vin: vehicle.dashboard().instruments
            for vehicle in self._connection.vehicles
        }

        return self.async_show_progress_done(next_step_id="select_vehicle")

    async def async_step_select_vehicle(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle select vehicle step."""
        if user_input is not None:
            self._init_info[CONF_VEHICLE] = user_input[CONF_VEHICLE]
            return await self.async_step_select_instruments()

        # Check if vehicles were discovered
        if "CONF_VEHICLES" not in self._init_info:
            _LOGGER.debug("No vehicles found in init info, restarting flow")
            return await self.async_step_user()

        vin_numbers = self._init_info["CONF_VEHICLES"].keys()
        return self.async_show_form(
            step_id="select_vehicle",
            errors=self._errors,
            data_schema=vol.Schema({vol.Required(CONF_VEHICLE): vol.In(vin_numbers)}),
        )

    async def async_step_select_instruments(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle select instruments step."""
        instruments = self._init_info["CONF_VEHICLES"][self._init_info[CONF_VEHICLE]]
        instruments_dict = {
            instrument.attr: instrument.name for instrument in instruments
        }

        if user_input is not None:
            self._init_info.pop("CONF_VEHICLES", None)

            if not self._init_info[CONF_NAME]:
                self._init_info[CONF_NAME] = self._init_info[CONF_VEHICLE]

            await self.async_set_unique_id(self._init_info[CONF_VEHICLE])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._init_info[CONF_NAME],
                data=self._init_info,
                options={
                    CONF_RESOURCES: user_input[CONF_RESOURCES],
                    CONF_AVAILABLE_RESOURCES: instruments_dict,
                },
            )

        return self.async_show_form(
            step_id="select_instruments",
            errors=self._errors,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_RESOURCES, default=list(instruments_dict.keys())
                    ): cv.multi_select(instruments_dict)
                }
            ),
            last_step=True,
        )

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        """Handle reauth for Volkswagen Connect."""
        entry_id = self.context.get("entry_id")
        self._entry = self.hass.config_entries.async_get_entry(entry_id)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle re-authentication with Volkswagen Connect."""
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._entry is not None
            _LOGGER.debug("Creating connection to Volkswagen Connect for reauth")
            self._connection = Connection(
                session=async_get_clientsession(self.hass),
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                country=self._entry.options.get(
                    CONF_REGION, self._entry.data[CONF_REGION]
                ),
            )

            try:
                await self._connection.doLogin()

                if not await self._connection.validate_login():
                    _LOGGER.warning(
                        "Unable to login to Volkswagen Connect. "
                        "May need to accept a new EULA. "
                        "Try logging in to the portal: https://www.myvolkswagen.net/"
                    )
                    errors["base"] = "cannot_connect"
                else:
                    data = self._entry.data.copy()
                    self.hass.config_entries.async_update_entry(
                        self._entry,
                        data={
                            **data,
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
                    await self.hass.config_entries.async_reload(self._entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOGGER.error("Failed to login during reauth: %s", err)
                errors["base"] = "cannot_connect"

        assert self._entry is not None
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=self._entry.data[CONF_USERNAME]
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get the options flow for this handler."""
        return VolkswagenCarnetOptionsFlowHandler(config_entry)


class VolkswagenCarnetOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Volkswagen Connect options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry
        self._errors: dict[str, str] = {}
        self._data: dict = {}

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle user options step."""
        if user_input is not None:
            self._data = user_input
            return await self.async_step_select_instruments()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SPIN,
                        default=self._config_entry.data.get(CONF_SPIN, ""),
                    ): str,
                    vol.Optional(
                        CONF_REGION,
                        default=self._config_entry.options.get(
                            CONF_REGION, self._config_entry.data[CONF_REGION]
                        ),
                    ): str,
                    vol.Optional(
                        CONF_MUTABLE,
                        default=self._config_entry.data.get(CONF_MUTABLE, True),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_CONVERT,
                        default=self._config_entry.data.get(
                            CONF_CONVERT, CONF_NO_CONVERSION
                        ),
                    ): vol.In(CONVERT_DICT),
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self._config_entry.data.get(
                                CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL
                            ),
                        ),
                    ): cv.positive_int,
                }
            ),
        )

    async def async_step_select_instruments(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle select instruments step."""
        coordinator = await get_coordinator(self.hass, self._config_entry)
        data = self._config_entry.as_dict()

        vehicle: Vehicle = get_vehicle(coordinator=coordinator)
        instruments = vehicle.dashboard().instruments
        instruments_dict = {
            instrument.attr: instrument.name for instrument in instruments
        }

        if user_input is not None:
            old_resources = set(data.get("options", {}).get(CONF_RESOURCES, []))
            new_resources = set(user_input[CONF_RESOURCES])

            removed_resources = old_resources - new_resources
            added_resources = new_resources - old_resources

            if removed_resources or added_resources:
                _LOGGER.info(
                    "Resources changed - adding: %s, removing: %s",
                    added_resources,
                    removed_resources,
                )

            # Recreate entities if resources changed or conversion changed
            old_convert = data.get("data", {}).get(CONF_CONVERT, CONF_NO_CONVERSION)
            new_convert = self._data.get(CONF_CONVERT, CONF_NO_CONVERSION)
            recreate_entities = bool(removed_resources) or (old_convert != new_convert)

            if recreate_entities:
                _LOGGER.debug("Recreating entities due to configuration changes")
                entity_registry = async_get(self.hass)
                entity_registry.async_clear_config_entry(self._config_entry.entry_id)

            # Update data with input from previous steps
            data["data"].update(self._data)

            # Update config entry data
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**data["data"]},
            )

            # Set options
            return self.async_create_entry(
                title="",
                data={
                    **data.get("options", {}),
                    CONF_RESOURCES: user_input[CONF_RESOURCES],
                    CONF_AVAILABLE_RESOURCES: instruments_dict,
                },
            )

        selected = {
            i
            for i in instruments_dict
            if i in data.get("options", {}).get(CONF_RESOURCES, [])
        }

        return self.async_show_form(
            step_id="select_instruments",
            errors=self._errors,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_RESOURCES, default=list(selected)
                    ): cv.multi_select(instruments_dict)
                }
            ),
            last_step=True,
        )
