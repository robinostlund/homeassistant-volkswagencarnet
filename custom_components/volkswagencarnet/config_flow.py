import logging
from typing import Optional

import homeassistant.helpers.config_validation as cv
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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get
from volkswagencarnet.vw_connection import Connection
from volkswagencarnet.vw_vehicle import Vehicle

from .const import (
    CONF_CONVERT,
    CONF_DEBUG,
    CONVERT_DICT,
    CONF_MUTABLE,
    CONF_REGION,
    CONF_REPORT_REQUEST,
    CONF_REPORT_SCAN_INTERVAL,
    CONF_SPIN,
    CONF_VEHICLE,
    DEFAULT_REGION,
    DEFAULT_REPORT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    DEFAULT_DEBUG,
    CONF_AVAILABLE_RESOURCES,
    CONF_NO_CONVERSION,
)
from .util import get_coordinator, get_vehicle

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = {
    vol.Optional(CONF_NAME, default=""): str,
    vol.Required(CONF_USERNAME, default=""): str,
    vol.Required(CONF_PASSWORD, default=""): str,
    vol.Optional(CONF_SPIN, default=""): str,
    vol.Optional(CONF_REGION, default=DEFAULT_REGION): str,
    vol.Optional(CONF_MUTABLE, default=True): cv.boolean,
    vol.Optional(CONF_CONVERT, default=CONF_NO_CONVERSION): vol.In(CONVERT_DICT),
    vol.Optional(CONF_DEBUG, default=DEFAULT_DEBUG): cv.boolean,
}


class VolkswagenCarnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3
    task_login = None
    task_finish = None
    entry = None

    def __init__(self):
        """Initialize."""
        self._entry: Optional[ConfigEntry] = None
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
                fulldebug=self._init_info.get(CONF_DEBUG, DEFAULT_DEBUG),
                country=self._init_info[CONF_REGION],
            )

            return await self.async_step_login()

        return self.async_show_form(step_id="user", data_schema=vol.Schema(DATA_SCHEMA), errors=self._errors)

    # noinspection PyBroadException
    async def _async_task_login(self):
        try:
            await self._connection.doLogin()
        except Exception as e:
            _LOGGER.error("Failed to login due to error: %s", str(e))
            self._errors["base"] = "cannot_connect"

        if not self._connection.logged_in:
            self._errors["base"] = "cannot_connect"

        self.hass.async_create_task(self.hass.config_entries.flow.async_configure(flow_id=self.flow_id))

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
        instruments = self._init_info["CONF_VEHICLES"][self._init_info[CONF_VEHICLE]]
        instruments_dict = {instrument.attr: instrument.name for instrument in instruments}

        if user_input is not None:
            # self._init_info[CONF_RESOURCES] = user_input[CONF_RESOURCES]
            self._init_info.pop("CONF_VEHICLES", None)

            if self._init_info[CONF_NAME] is None or self._init_info[CONF_NAME] == "":
                self._init_info[CONF_NAME] = self._init_info[CONF_VEHICLE]

            await self.async_set_unique_id(self._init_info[CONF_VEHICLE])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._init_info[CONF_NAME],
                data=self._init_info,
                options={CONF_RESOURCES: user_input[CONF_RESOURCES], CONF_AVAILABLE_RESOURCES: instruments_dict},
            )

        return self.async_show_form(
            step_id="select_instruments",
            errors=self._errors,
            data_schema=vol.Schema(
                {vol.Optional(CONF_RESOURCES, default=list(instruments_dict.keys())): cv.multi_select(instruments_dict)}
            ),
            last_step=True,
        )

    async def async_step_login(self, user_input=None):
        if not self.task_login:
            self.task_login = self.hass.async_create_task(self._async_task_login())

            return self.async_show_progress(
                step_id="login",
                progress_action="task_login",
            )

        # noinspection PyBroadException
        try:
            await self.task_login
        except Exception:
            return self.async_abort(reason="Failed to connect to WeConnect")

        if self._errors:
            return self.async_show_progress_done(next_step_id="user")

        for vehicle in self._connection.vehicles:
            _LOGGER.info(f"Found data for VIN: {vehicle.vin} from WeConnect")

        self._init_info["CONF_VEHICLES"] = {
            vehicle.vin: vehicle.dashboard().instruments for vehicle in self._connection.vehicles
        }

        return self.async_show_progress_done(next_step_id="select_vehicle")

    async def async_step_reauth(self, entry) -> dict:
        """Handle initiation of re-authentication with WeConnect."""
        self.entry = entry
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict = None) -> dict:
        """Handle re-authentication with WeConnect."""
        errors: dict = {}

        if user_input is not None:
            _LOGGER.debug("Creating connection to volkswagen WeConnect")
            self._connection = Connection(
                session=async_get_clientsession(self.hass),
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                fulldebug=self.entry.options.get(CONF_DEBUG, self.entry.data.get(CONF_DEBUG, DEFAULT_DEBUG)),
                country=self.entry.options.get(CONF_REGION, self.entry.data[CONF_REGION]),
            )

            # noinspection PyBroadException
            try:
                await self._connection.doLogin()

                if not await self._connection.validate_login:
                    _LOGGER.debug(
                        "Unable to login to WeConnect. Need to accept a new EULA? Try logging in to the portal: https://www.portal.volkswagen-we.com/"
                    )
                    errors["base"] = "cannot_connect"
                else:
                    data = self.entry.data.copy()
                    self.hass.config_entries.async_update_entry(
                        self.entry,
                        data={
                            **data,
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
                    self.hass.async_create_task(self.hass.config_entries.async_reload(self.entry.entry_id))

                    return self.async_abort(reason="reauth_successful")
            except Exception as e:
                _LOGGER.error("Failed to login due to error: %s", str(e))
                return self.async_abort(reason="Failed to connect to WeConnect")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self.entry.data[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

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
        self._session = None
        self._errors = {}

        self._config_entry: ConfigEntry = config_entry
        self._data = {}

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            self._data = user_input
            return await self.async_step_select_instruments()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_REPORT_REQUEST,
                        default=self._config_entry.options.get(
                            CONF_REPORT_REQUEST, self._config_entry.data.get(CONF_REPORT_REQUEST, False)
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DEBUG,
                        default=self._config_entry.options.get(
                            CONF_DEBUG, self._config_entry.data.get(CONF_DEBUG, DEFAULT_DEBUG)
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_CONVERT, default=self._config_entry.data.get(CONF_CONVERT, CONF_NO_CONVERSION)
                    ): vol.In(CONVERT_DICT),
                    vol.Optional(
                        CONF_REPORT_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_REPORT_SCAN_INTERVAL,
                            self._config_entry.data.get(CONF_REPORT_SCAN_INTERVAL, DEFAULT_REPORT_UPDATE_INTERVAL),
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL, self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_REGION,
                        default=self._config_entry.options.get(CONF_REGION, self._config_entry.data[CONF_REGION]),
                    ): str,
                }
            ),
        )

    async def async_step_select_instruments(self, user_input=None):
        coordinator = await get_coordinator(self.hass, self._config_entry)
        data = self._config_entry.as_dict()

        v: Vehicle = get_vehicle(coordinator=coordinator)
        d = v.dashboard()

        instruments_dict = {instrument.attr: instrument.name for instrument in d.instruments}

        if user_input is not None:
            options = {
                **data["options"],
                CONF_RESOURCES: user_input[CONF_RESOURCES],
                CONF_AVAILABLE_RESOURCES: instruments_dict,
            }

            removed_resources = set(data.get("options", {}).get("resources", {})) - set(options[CONF_RESOURCES])
            added_resources = set(options[CONF_RESOURCES]) - set(data.get("options", {}).get("resources", {}))

            _LOGGER.info(f"Adding resources: {added_resources}, removing resources: {removed_resources}")

            # Need to recreate entitiesin some cases
            # Some resource was removed
            recreate_entities = len(removed_resources) > 0
            # distance conversion was changed
            recreate_entities = recreate_entities or self._data[CONF_CONVERT] != data.get("data", {}).get(
                CONF_CONVERT, ""
            )

            if recreate_entities:
                entity_registry = async_get(self.hass)
                # Remove all HA entities because we don't know which entities a resource has created :/
                # All entities will be recreated automatically anyway.
                entity_registry.async_clear_config_entry(self._config_entry.entry_id)

            # Update data with input from previous steps
            data.get("data").update(self._data)
            # Update the data first
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**data["data"]},
            )

            # Set options
            return self.async_create_entry(title="", data=options)

        selected = {i for i in instruments_dict if i in data["options"][CONF_RESOURCES]}

        return self.async_show_form(
            step_id="select_instruments",
            errors=self._errors,
            data_schema=vol.Schema(
                {vol.Optional(CONF_RESOURCES, default=list(selected)): cv.multi_select(instruments_dict)}
            ),
            last_step=True,
        )
