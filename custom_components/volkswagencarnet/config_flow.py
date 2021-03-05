import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import InvalidURL
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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from volkswagencarnet import Connection

from .const import (
    CONF_MUTABLE,
    CONF_REGION,
    CONF_REPORT_REQUEST,
    CONF_REPORT_SCAN_INTERVAL,
    CONF_SCANDINAVIAN_MILES,
    CONF_SPIN,
    CONF_VEHICLE,
    DEFAULT_REGION,
    DEFAULT_REPORT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = {
    vol.Optional(CONF_NAME, default=""): str,
    vol.Required(CONF_USERNAME, default=""): str,
    vol.Required(CONF_PASSWORD, default=""): str,
    vol.Optional(CONF_SPIN, default=""): str,
    vol.Optional(CONF_REGION, default=DEFAULT_REGION): str,
    vol.Optional(CONF_MUTABLE, default=True): cv.boolean,
    vol.Optional(CONF_SCANDINAVIAN_MILES, default=False): cv.boolean,
}


class VolkswagenCarnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    task_login = None
    task_update = None
    task_finish = None

    def __init__(self):
        """Initialize."""
        self._init_info = {}
        self._errors = {}
        self._connection = None
        self._session = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.task_login = None
            self.task_update = None
            self.task_finish = None
            self._errors = {}
            self._init_info = user_input

            _LOGGER.debug("Creating connection to volkswagen weconnect")
            self._connection = Connection(
                session=async_get_clientsession(self.hass),
                username=self._init_info[CONF_USERNAME],
                password=self._init_info[CONF_PASSWORD],
            )

            # if await self._async_retrieve_vehicles():
            return await self.async_step_login()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(DATA_SCHEMA), errors=self._errors
        )

    async def _async_task_login(self):
        await self._connection._login()

        if not self._connection.logged_in:
            self._errors["base"] = "cannot_connect"

        self.hass.async_create_task(
            self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
        )

    async def _async_task_update(self):
        _LOGGER.debug("UPDATE STARTED!")

        if not await self._connection.update():
            self._errors["base"] = "cannot_update"

        _LOGGER.debug("UPDATE DONE!")

        self.hass.async_create_task(
            self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
        )

    async def async_step_select_vehicle(self, user_input=None):
        if user_input is not None:
            self._init_info[CONF_VEHICLE] = user_input[CONF_VEHICLE]

            return await self.async_step_select_instruments()

        vin_numbers = self._init_info["CONF_VEHICLES"].keys()
        return self.async_show_form(
            step_id="select_vehicle",
            errors=self._errors,
            data_schema=vol.Schema({vol.Required(CONF_VEHICLE): vol.In(vin_numbers)}),
        )

    async def async_step_select_instruments(self, user_input=None):
        if user_input is not None:
            self._init_info[CONF_RESOURCES] = user_input[CONF_RESOURCES]
            del self._init_info["CONF_VEHICLES"]

            if self._init_info[CONF_NAME] is None:
                self._init_info[CONF_NAME] = self._init_info[CONF_VEHICLE]

            await self.async_set_unique_id(self._init_info[CONF_VEHICLE])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._init_info[CONF_NAME], data=self._init_info
            )

        instruments = self._init_info["CONF_VEHICLES"][self._init_info[CONF_VEHICLE]]
        instruments_dict = {
            instrument.attr: instrument.name for instrument in instruments
        }
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
        )

    async def async_step_login(self, user_input=None):
        if not self.task_login or not self.task_update:
            if not self.task_login and not self._connection.logged_in:
                self.task_login = self.hass.async_create_task(self._async_task_login())
                progress_action = "task_login"
            else:
                self.task_update = self.hass.async_create_task(
                    self._async_task_update()
                )
                progress_action = "task_update"

            return self.async_show_progress(
                step_id="login",
                progress_action=progress_action,
            )

        try:
            await self.task_update
        except InvalidURL:
            return self.async_abort("Failed to connect to WeConnect")

        if self._errors:
            return self.async_show_progress_done(next_step_id="user")

        _LOGGER.debug("Updating data from volkswagen WeConnect")
        for vehicle in self._connection.vehicles:
            _LOGGER.info(f"Found data for VIN: {vehicle.vin} from WeConnect")

        self._init_info["CONF_VEHICLES"] = {
            vehicle.vin: vehicle.dashboard().instruments
            for vehicle in self._connection.vehicles
        }

        return self.async_show_progress_done(next_step_id="select_vehicle")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return VolkswagenCarnetOptionsFlowHandler(config_entry)


class VolkswagenCarnetOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Plaato options."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize domain options flow."""
        super().__init__()

        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_REPORT_REQUEST,
                        default=self._config_entry.options.get(
                            CONF_REPORT_REQUEST, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_REPORT_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_REPORT_SCAN_INTERVAL, DEFAULT_REPORT_UPDATE_INTERVAL
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): cv.positive_int,
                }
            ),
        )
