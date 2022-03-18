"""Services exposed to Home Assistant."""
import logging
from datetime import datetime, timezone

import pytz
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from volkswagencarnet.vw_timer import Timer, TimerData

from .util import get_coordinator_by_device_id, get_vehicle, validate_charge_max_current

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_CHARGER_MAX_CURRENT_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Optional("max_current"): vol.In([5, 10, 13, 16, 32, "5", "10", "13", "16", "32", "reduced", "max"]),
    },
    extra=vol.ALLOW_EXTRA,  # FIXME, should not be needed
)

SERVICE_UPDATE_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("timer_id"): vol.In([1, 2, 3]),
        vol.Optional("charging_profile"): vol.All(cv.positive_int, vol.Range(min_included=1, max_included=10)),
        vol.Optional("enabled"): vol.All(cv.boolean),
        vol.Optional("frequency"): vol.In(["cyclic", "single"]),
        vol.Optional("departure_time"): vol.All(cv.string),
        vol.Optional("departure_datetime"): vol.All(cv.string),
        vol.Optional("weekday_mask"): vol.All(cv.string, vol.Length(min=7, max=7)),
    },
    extra=vol.ALLOW_EXTRA,  # FIXME, should not be needed
)

SERVICE_SET_TIMER_BASIC_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Optional("min_level"): vol.In([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]),
        vol.Optional("target_temperature_celsius"): vol.Any(cv.string, cv.positive_int),
        vol.Optional("target_temperature_fahrenheit"): vol.Any(cv.string, cv.positive_int),
    },
    extra=vol.ALLOW_EXTRA,  # FIXME, should not be needed
)

SERVICE_UPDATE_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("profile_id"): vol.All(cv.positive_int, vol.Range(min_included=1, max_included=10)),
        vol.Optional("profile_name"): vol.All(cv.string),
        vol.Optional("charging"): vol.All(cv.boolean),
        vol.Optional("climatisation"): vol.All(cv.boolean),
        vol.Optional("target_level"): vol.In(
            [
                0,
                10,
                20,
                30,
                40,
                50,
                60,
                70,
                80,
                90,
                100,
                "0",
                "10",
                "20",
                "30",
                "40",
                "50",
                "60",
                "70",
                "80",
                "90",
                "100",
            ]
        ),
        vol.Optional("charge_max_current"): vol.In([5, 10, 13, 16, 32, "5", "10", "13", "16", "32", "reduced", "max"]),
        vol.Optional("night_rate"): vol.All(cv.boolean),
        vol.Optional("night_rate_start"): vol.All(cv.string),
        vol.Optional("night_rate_end"): vol.All(cv.string),
    },
    extra=vol.ALLOW_EXTRA,  # FIXME, should not be needed
)


class SchedulerService:
    """Schedule services class."""

    def __init__(self, hass: HomeAssistant):
        """Init."""
        self.hass: HomeAssistant = hass

    async def set_timer_basic_settings(self, service_call: ServiceCall) -> bool:
        """Service for configuring basic settings."""
        c = await get_coordinator_by_device_id(self.hass, service_call.data.get("device_id"))
        v = get_vehicle(c)

        # parse service call
        tt = service_call.data.get("target_temperature", None)
        ml = service_call.data.get("min_level", None)
        # hs = service_call.data.get("heater_source", None)
        res = True

        # update timers accordingly (not working)
        # if hs is not None:
        #     _LOGGER.debug(f"Setting heater source to {hs}")
        #     # get timers
        #     t = await c.connection.getTimers(c.vin)
        #     t.timersAndProfiles.timerBasicSetting.set_heater_source(hs)
        #     res = await c.connection._setDepartureTimer(c.vin, t.timersAndProfiles, "setHeaterSource")
        #     # res = await v.set_departure_timer_heater_source(hs)
        #     _LOGGER.debug(f"set heater source returned {res}")
        if tt is not None:
            _LOGGER.debug(f"Setting target temperature to {tt} {self.hass.config.units.temperature_unit}")
            # get timers
            t = await c.connection.getTimers(c.vin)
            if self.hass.config.units.is_metric:
                t.timersAndProfiles.timerBasicSetting.set_target_temperature_celsius(float(tt))
            else:
                t.timersAndProfiles.timerBasicSetting.set_target_temperature_fahrenheit(int(tt))
            # send command to volkswagencarnet
            res = res and await v.set_climatisation_temp(t.timersAndProfiles.timerBasicSetting.targetTemperature)
        if ml is not None:
            _LOGGER.debug(f"Setting minimum charge level to {ml}%")
            # send charge limit command to volkswagencarnet
            res = res and await v.set_charge_min_level(int(ml))

        self.hass.add_job(c.async_request_refresh)

        return res

    async def update_schedule(self, service_call: ServiceCall) -> bool:
        """Service for updating departure schedules."""
        c = await get_coordinator_by_device_id(self.hass, service_call.data.get("device_id"))
        v = get_vehicle(c)

        data: TimerData = await c.connection.getTimers(c.vin)
        if data is None:
            raise Exception("No timers found")

        timer_id = int(service_call.data.get("timer_id", -1))
        charging_profile = service_call.data.get("charging_profile", None)
        enabled = service_call.data.get("enabled", None)
        frequency = service_call.data.get("frequency", None)
        departure_time = service_call.data.get("departure_time", None)
        departure_datetime = service_call.data.get("departure_datetime", None)
        weekday_mask = service_call.data.get("weekday_mask", None)

        timers: dict[int, Timer] = {1: data.get_schedule(1), 2: data.get_schedule(2), 3: data.get_schedule(3)}
        if frequency is not None:
            timers[timer_id].timerFrequency = frequency
            if frequency == "single":
                if isinstance(departure_datetime, int):
                    time = datetime.fromtimestamp(departure_datetime)
                elif isinstance(departure_datetime, str):
                    time = datetime.fromisoformat(departure_datetime)
                else:
                    time = departure_datetime
                if time.tzinfo is None:
                    time.replace(tzinfo=pytz.timezone(self.hass.config.time_zone))
                time = time.astimezone(timezone.utc)
                timers[timer_id].departureDateTime = time.strftime("%Y-%m-%dT%H:%M")
                timers[timer_id].departureTimeOfDay = time.strftime("%H:%M")
            elif frequency == "cyclic":
                timers[timer_id].departureDateTime = None
                timers[timer_id].departureTimeOfDay = self.time_to_utc(departure_time)
                timers[timer_id].departureWeekdayMask = weekday_mask
            else:
                raise Exception(f"Invalid frequency: {frequency}")

        if charging_profile is not None:
            timers[timer_id].profileID = charging_profile

        if enabled is not None:
            timers[timer_id].timerProgrammedStatus = "programmed" if enabled else "notProgrammed"

        _LOGGER.debug(f"Updating timer {timers[timer_id].json_updated['timer']}")
        data.timersAndProfiles.timerList.timer = [timers[1], timers[2], timers[3]]
        res = await v.set_schedule(data)
        self.hass.add_job(c.async_request_refresh)
        return res

    async def update_profile(self, service_call: ServiceCall) -> bool:
        """Service for updating charging profiles (locations)."""
        c = await get_coordinator_by_device_id(self.hass, service_call.data.get("device_id"))
        v = get_vehicle(coordinator=c)

        data: TimerData = await c.connection.getTimers(c.vin)
        if data is None:
            raise Exception("No profiles found")

        profile_id = int(service_call.data.get("profile_id", -1))
        profile_name = service_call.data.get("profile_name", None)
        charging = service_call.data.get("charging", None)
        charge_max_current = service_call.data.get("charge_max_current", None)
        climatisation = service_call.data.get("climatisation", None)
        target_level = service_call.data.get("target_level", None)
        night_rate = service_call.data.get("night_rate", None)
        night_rate_start = service_call.data.get("night_rate_start", None)
        night_rate_end = service_call.data.get("night_rate_end", None)
        # heater_source = service_call.data.get("heater_source", None)

        # update timers accordingly
        charge_max_current = validate_charge_max_current(charge_max_current)

        profile = data.get_profile(profile_id)
        profile.profileName = profile_name if profile_name is not None else profile.profileName
        profile.operationCharging = charging if charging is not None else profile.operationCharging
        profile.chargeMaxCurrent = charge_max_current if charge_max_current is not None else profile.chargeMaxCurrent
        profile.operationClimatisation = climatisation if climatisation is not None else profile.operationClimatisation
        profile.targetChargeLevel = target_level if target_level is not None else profile.targetChargeLevel
        profile.nightRateActive = night_rate if night_rate is not None else profile.nightRateActive

        if night_rate_start is not None:
            profile.nightRateTimeStart = self.time_to_utc(night_rate_start)
        if night_rate_end is not None:
            profile.nightRateTimeEnd = self.time_to_utc(night_rate_end)
        # if heater_source is not None:
        #    data.timersAndProfiles.timerBasicSetting.set_heater_source(heater_source)

        _LOGGER.debug(f"Updating profile {profile.profileID}: {profile.profileName}")
        res = await v.set_schedule(data)
        self.hass.add_job(c.async_request_refresh)
        return res

    def time_to_utc(self, time_string: str) -> str:
        """Convert a local time string to UTC equivalent."""
        tz = pytz.timezone(self.hass.config.time_zone)
        target = tz.normalize(datetime.now().replace(tzinfo=tz)).replace(
            hour=int(time_string[0:2]), minute=int(time_string[3:5])
        )
        ret = target.astimezone(pytz.utc)
        return ret.strftime("%H:%M")


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
