"""Services exposed to Home Assistant."""

import logging
from datetime import datetime, timezone

import pytz
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from volkswagencarnet.vw_timer import Timer, TimerData

from .util import get_coordinator_by_device_id, get_vehicle

_LOGGER = logging.getLogger(__name__)


SERVICE_UPDATE_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("timer_id"): vol.In([1, 2, 3]),
        vol.Optional("charging_profile"): vol.All(
            cv.positive_int, vol.Range(min_included=1, max_included=10)
        ),
        vol.Optional("enabled"): vol.All(cv.boolean),
        vol.Optional("charging"): vol.All(cv.boolean),
        vol.Optional("climatisation"): vol.All(cv.boolean),
        vol.Optional("frequency"): vol.In(["recurring", "single"]),
        vol.Optional("departure_time"): cv.time,
        vol.Optional("departure_datetime"): cv.datetime,
        vol.Optional("weekdays"): vol.All(
            cv.ensure_list,
            [
                vol.In(
                    [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ]
                )
            ],
        ),
        vol.Optional("preferred_charging_times_enabled"): vol.All(cv.boolean),
        vol.Optional("preferred_charging_times_start_time"): cv.time,
        vol.Optional("preferred_charging_times_end_time"): cv.time,
    },
)


class SchedulerService:
    """Schedule services class."""

    def __init__(self, hass: HomeAssistant):
        """Init."""
        self.hass: HomeAssistant = hass

    async def update_schedule(self, service_call: ServiceCall) -> None:
        """Service for updating departure schedules."""
        try:
            timer_id = int(service_call.data.get("timer_id", -1))
            if timer_id not in [1, 2, 3]:
                raise HomeAssistantError(
                    f"Invalid timer_id: {timer_id}. Must be 1, 2, or 3"
                )

            coordinator = await get_coordinator_by_device_id(
                self.hass, service_call.data.get("device_id")
            )
            
            # Access the already-loaded vehicle directly from coordinator
            if coordinator.vehicle is None:
                raise HomeAssistantError("Vehicle data not available")
            
            vehicle = coordinator.vehicle
            
            # Check if timer is supported
            if not vehicle.is_departure_timer_supported(timer_id):
                raise HomeAssistantError(
                    f"Timer {timer_id} is not supported for this vehicle"
                )
            
            _LOGGER.info("Timer %s validated for VIN %s", timer_id, vehicle.vin)

            # charging_profile = service_call.data.get("charging_profile", None)
            # enabled = service_call.data.get("enabled", None)
            # frequency = service_call.data.get("frequency", None)
            # departure_time = service_call.data.get("departure_time", None)
            # departure_datetime = service_call.data.get("departure_datetime", None)
            # weekday_mask = service_call.data.get("weekday_mask", None)

            # timers: dict[int, Timer] = {
            #     1: data.get_schedule(1),
            #     2: data.get_schedule(2),
            #     3: data.get_schedule(3),
            # }

            # if frequency is not None:
            #     timers[timer_id].timerFrequency = frequency
            #     if frequency == "single":
            #         if isinstance(departure_datetime, int):
            #             time = datetime.fromtimestamp(departure_datetime)
            #         elif isinstance(departure_datetime, str):
            #             time = datetime.fromisoformat(departure_datetime)
            #         else:
            #             time = departure_datetime
            #         if time.tzinfo is None:
            #             time = time.replace(
            #                 tzinfo=pytz.timezone(self.hass.config.time_zone)
            #             )
            #         time = time.astimezone(timezone.utc)
            #         timers[timer_id].departureDateTime = time.strftime("%Y-%m-%dT%H:%M")
            #         timers[timer_id].departureTimeOfDay = time.strftime("%H:%M")
            #     elif frequency == "cyclic":
            #         timers[timer_id].departureDateTime = None
            #         timers[timer_id].departureTimeOfDay = self.time_to_utc(
            #             departure_time
            #         )
            #         timers[timer_id].departureWeekdayMask = weekday_mask
            #     else:
            #         raise HomeAssistantError(f"Invalid frequency: {frequency}")

            # if charging_profile is not None:
            #     timers[timer_id].profileID = charging_profile

            # if enabled is not None:
            #     timers[timer_id].timerProgrammedStatus = (
            #         "programmed" if enabled else "notProgrammed"
            #     )

            # _LOGGER.debug("Updating timer %s", timer_id)
            # data.timersAndProfiles.timerList.timer = [timers[1], timers[2], timers[3]]
            # result = await v.set_schedule(data)
            # if result is False:
            #     raise HomeAssistantError(
            #         f"Failed to update schedule for timer {timer_id}"
            #     )

            # self.hass.add_job(c.async_request_refresh)
            # _LOGGER.info("Successfully updated schedule for timer %s", timer_id)

        except HomeAssistantError:
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error in update_schedule: %s", err)
            raise HomeAssistantError(f"Failed to update schedule: {err}") from err
