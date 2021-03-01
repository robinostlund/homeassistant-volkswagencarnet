import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from volkswagencarnet import Connection
from .const import (
    DOMAIN,
    CONF_REGION,
    DEFAULT_REGION,
    CONF_MUTABLE,
    CONF_SPIN,
    DEFAULT_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    CONF_SCANDINAVIAN_MILES,
    RESOURCES_DICT,
    CONF_VEHICLE
)
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = {
    vol.Optional(CONF_NAME, default=""): str,
    vol.Required(CONF_USERNAME, default=""): str,
    vol.Required(CONF_PASSWORD, default=""): str,
    vol.Optional(CONF_REGION, default=DEFAULT_REGION): str,
    vol.Optional(CONF_MUTABLE, default=True): cv.boolean,
    vol.Optional(CONF_SPIN, default=""): str,
    vol.Optional(CONF_RESOURCES,
                 default=list(RESOURCES_DICT.keys())): cv.multi_select(
        RESOURCES_DICT),
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
            step_id="user",
            data_schema=vol.Schema(DATA_SCHEMA),
            errors=self._errors
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

            if self._init_info[CONF_NAME] is None:
                self._init_info[CONF_NAME] = self._init_info[CONF_VEHICLE]

            await self.async_set_unique_id(self._init_info[CONF_VEHICLE])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=self._init_info[CONF_NAME],
                                    data=self._init_info)

        return self.async_show_form(
            step_id="select_vehicle",
            errors=self._errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VEHICLE): vol.In(
                        list(self._init_info["CONF_VEHICLES"]))
                }
            )
        )

    async def async_step_login(self, user_input=None):
        if not self.task_login or not self.task_update:
            if not self.task_login and not self._connection.logged_in:
                self.task_login = self.hass.async_create_task(
                    self._async_task_login())
                progress_action = "task_login"
            else:
                self.task_update = self.hass.async_create_task(
                    self._async_task_update())
                progress_action = "task_update"

            return self.async_show_progress(
                step_id="login",
                progress_action=progress_action,
            )

        await self.task_update

        if self._errors:
            return self.async_show_progress_done(next_step_id="user")

        _LOGGER.debug("Updating data from volkswagen carnet")
        for vehicle in self._connection.vehicles:
            _LOGGER.info(f"Found data for VIN: {vehicle.vin} from carnet")

        self._init_info["CONF_VEHICLES"] = [vehicle.vin for vehicle in
                                            self._connection.vehicles]

        return self.async_show_progress_done(next_step_id="select_vehicle")


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
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ): (
                        vol.All(cv.time_period,
                                vol.Clamp(min=MIN_UPDATE_INTERVAL))
                    )
                }
            ),
        )
