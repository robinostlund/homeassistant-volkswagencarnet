"""Services exposed to Home Assistant."""
import logging
from datetime import datetime, timezone
from typing import Optional, Union

import pytz
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry
from volkswagencarnet.vw_timer import Timer, TimerData
from volkswagencarnet.vw_vehicle import Vehicle

from .const import DOMAIN
from .error import ServiceError

_LOGGER = logging.getLogger(__name__)


def validate_charge_max_current(charge_max_current: Optional[Union[int, str]]):
    """
    Dummy implementation.

    Maybe there is a way to actually check which values the car supports?
    """
    return (
        charge_max_current is None
        or charge_max_current == "max"
        or str(charge_max_current) in ["0", "5", "10", "13", "16", "32"]
    )
    pass


async def get_coordinator(hass: HomeAssistant, service_call: ServiceCall):
    """Get the VolkswagenCoordinator."""
    registry: DeviceRegistry = device_registry.async_get(hass)
    dev_entry: DeviceEntry = registry.async_get(service_call.data.get("device_id"))

    # Get coordinator handling the device entry
    config_entry = hass.config_entries.async_get_entry(list(dev_entry.config_entries)[0])
    if config_entry.domain != DOMAIN:
        raise ServiceError("Unknown entity")
    coordinator = config_entry.data.get(
        "coordinator",
    )
    if coordinator is None:
        coordinator = hass.data[DOMAIN][config_entry.entry_id]["data"].coordinator
    if coordinator is None:
        raise ServiceError("Unknown entity")
    return coordinator


def get_vehicle(coordinator) -> Vehicle:
    """Find requested vehicle."""
    # find VIN
    _LOGGER.debug(f"Found VIN {coordinator.vin}")
    # parse service call

    v: Optional[Vehicle] = None
    for vehicle in coordinator.connection.vehicles:
        if vehicle.vin.upper() == coordinator.vin:
            v = vehicle
            break
    if v is None:
        raise Exception("Vehicle not found")
    return v


class SchedulerService:
    """Schedule services class."""

    def __init__(self, hass: HomeAssistant):
        """Init."""
        self.hass: HomeAssistant = hass

    async def set_timer_basic_settings(self, service_call: ServiceCall):
        """Service for configuring basic settings."""
        c = await get_coordinator(self.hass, service_call)
        v = get_vehicle(c)

        # parse service call
        tt = service_call.data.get("target_temperature", None)
        ml = service_call.data.get("min_level", None)
        res = True

        # update timers accordingly
        if tt is not None:
            # get timers
            t = await c.connection.getTimers(c.vin)
            _LOGGER.debug(f"Setting target temperature to {tt} {self.hass.config.units.temperature_unit}")
            if self.hass.config.units.is_metric:
                t.timersAndProfiles.timerBasicSetting.set_target_temperature_celsius(float(tt))
            else:
                t.timersAndProfiles.timerBasicSetting.set_target_temperature_fahrenheit(int(tt))
            # send command to volkswagencarnet
            res = await v.set_climatisation_temp(t.timersAndProfiles.timerBasicSetting.targetTemperature)
        if ml is not None:
            _LOGGER.debug(f"Setting minimum charge level to {ml}%")
            # send charge limit command to volkswagencarnet
            res = res and await v.set_charge_min_level(int(ml))
        return res

    async def update_schedule(self, service_call: ServiceCall):
        """Service for updating departure schedules."""
        c = await get_coordinator(self.hass, service_call)
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
        return res

    async def update_profile(self, service_call: ServiceCall):
        """Service for updating charging profiles (locations)."""
        c = await get_coordinator(self.hass, service_call)
        v = get_vehicle(coordinator=c)

        data: TimerData = await c.connection.getTimers(c.vin)
        if data is None:
            raise Exception("No profiles found")

        profile_id = int(service_call.data.get("profile_id", -1))
        profile_name = int(service_call.data.get("profile_name", None))
        charging = service_call.data.get("charging", None)
        charge_max_current = service_call.data.get("charge_max_current", None)
        climatisation = service_call.data.get("climatisation", None)
        target_level = service_call.data.get("target_level", None)
        night_rate = service_call.data.get("night_rate", None)
        night_rate_start = service_call.data.get("night_rate_start", None)
        night_rate_end = service_call.data.get("night_rate_end", None)

        validate_charge_max_current(charge_max_current)

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

        _LOGGER.debug(f"Updating profile {profile}")
        res = await v.set_schedule(data)
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

    async def set_charger_max_current(self, service_call: ServiceCall):
        """Service for setting max charging current."""
        c = await get_coordinator(self.hass, service_call)
        v = get_vehicle(c)

        # parse service call
        level = service_call.data.get("max_current", None)

        # Apply
        return await v.set_charger_current(level)
