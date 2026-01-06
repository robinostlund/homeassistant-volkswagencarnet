"""Services exposed to Home Assistant."""

import logging
from datetime import datetime

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SPIN,
)
from .util import get_coordinator_by_device_id

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

            spin = coordinator.entry.data.get(CONF_SPIN, "")
            timer_attributes = vehicle.timer_attributes(timer_id)
            timer_raw = vehicle.departure_timer(timer_id)
            # Determine timer type from existing configuration
            is_ev_timer = timer_attributes.get("profile_id") is not None
            is_departure_timer = (
                "charging" in timer_raw
                or "climatisation" in timer_raw
                or "preferredChargingTimes" in timer_raw
            )
            is_aux_timer = not is_ev_timer and not is_departure_timer

            charging_profile = service_call.data.get("charging_profile", None)
            enabled = service_call.data.get("enabled", None)
            charging = service_call.data.get("charging", None)
            climatisation = service_call.data.get("climatisation", None)
            frequency = service_call.data.get("frequency", None)
            departure_time = service_call.data.get("departure_time", None)
            departure_datetime = service_call.data.get("departure_datetime", None)
            weekdays = service_call.data.get("weekdays", None)
            preferred_charging_times_enabled = service_call.data.get(
                "preferred_charging_times_enabled", None
            )
            preferred_charging_times_start_time = service_call.data.get(
                "preferred_charging_times_start_time", None
            )
            preferred_charging_times_end_time = service_call.data.get(
                "preferred_charging_times_end_time", None
            )

            # Validate parameters based on timer type
            self._validate_timer_parameters(
                is_departure_timer,
                is_ev_timer,
                is_aux_timer,
                charging_profile,
                enabled,
                charging,
                climatisation,
                frequency,
                departure_time,
                departure_datetime,
                weekdays,
                preferred_charging_times_enabled,
                preferred_charging_times_start_time,
                preferred_charging_times_end_time,
            )

            if is_ev_timer:
                # Build EV timer payload with charging profile
                payload = {
                    "id": timer_id,
                    "enabled": enabled if enabled is not None else False,
                    "profileIDs": [charging_profile],
                }

                if frequency == "recurring" and departure_time is not None:
                    # Build recurringTimer with recurring schedule
                    # Handle time object conversion properly
                    from datetime import time

                    if isinstance(departure_time, time):
                        # Convert time to datetime in local timezone, then to UTC
                        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
                        today = dt_util.now(local_tz).date()
                        local_dt = datetime.combine(today, departure_time)
                        if local_dt.tzinfo is None:
                            local_dt = local_dt.replace(tzinfo=local_tz)
                        utc_time = dt_util.as_utc(local_dt)
                    else:
                        # It's already a datetime
                        utc_time = dt_util.as_utc(departure_time)

                    # Build weekdays mapping
                    weekday_map = {
                        "Monday": "mondays",
                        "Tuesday": "tuesdays",
                        "Wednesday": "wednesdays",
                        "Thursday": "thursdays",
                        "Friday": "fridays",
                        "Saturday": "saturdays",
                        "Sunday": "sundays",
                    }

                    # Initialize all days to False
                    recurring_on = {day: False for day in weekday_map.values()}
                    # Set specified days to True
                    if weekdays:
                        for day in weekdays:
                            if day in weekday_map:
                                recurring_on[weekday_map[day]] = True

                    payload["recurringTimer"] = {
                        "startTime": utc_time.strftime("%H:%M"),
                        "recurringOn": recurring_on,
                    }

                elif frequency == "single" and departure_datetime is not None:
                    # Build singleTimer with one-time schedule
                    if isinstance(departure_datetime, int):
                        dt = datetime.fromtimestamp(departure_datetime)
                    elif isinstance(departure_datetime, str):
                        dt = datetime.fromisoformat(departure_datetime)
                    else:
                        dt = departure_datetime

                    # Convert to UTC using dt_util (non-blocking)
                    utc_dt = dt_util.as_utc(dt)

                    payload["singleTimer"] = {
                        "startDateTime": utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    }

                _LOGGER.debug("EV Departure Timer payload: %s", payload)
                _LOGGER.debug("Updating EV Departure Timer %s", timer_id)
                if is_departure_timer:
                    raise HomeAssistantError(f"Timer {timer_id} is a Departure timer.")
                if is_aux_timer:
                    raise HomeAssistantError(
                        f"Timer {timer_id} is an Auxiliary/AC timer."
                    )
                result = await vehicle.update_departure_timer(
                    timer_id=timer_id, spin=spin, timer_data=payload
                )
                if result is False:
                    raise HomeAssistantError(
                        f"Failed to update EV departure timer {timer_id}"
                    )

            elif is_departure_timer:
                # Build departure timer payload
                payload = {
                    "id": timer_id,
                    "enabled": enabled if enabled is not None else True,
                    "charging": charging if charging is not None else False,
                    "climatisation": climatisation
                    if climatisation is not None
                    else True,
                }

                # Handle recurring timer
                if frequency == "recurring" and departure_time is not None:
                    from datetime import time

                    if isinstance(departure_time, time):
                        time_str = departure_time.strftime("%H:%M")
                    else:
                        time_str = departure_time.strftime("%H:%M")

                    # Build repetitionDays array (lowercase day names)
                    weekday_map = {
                        "Monday": "monday",
                        "Tuesday": "tuesday",
                        "Wednesday": "wednesday",
                        "Thursday": "thursday",
                        "Friday": "friday",
                        "Saturday": "saturday",
                        "Sunday": "sunday",
                    }

                    repetition_days = []
                    if weekdays:
                        for day in weekdays:
                            if day in weekday_map:
                                repetition_days.append(weekday_map[day])

                    payload["recurringTimer"] = {
                        "departureTimeLocal": time_str,
                        "repetitionDays": repetition_days,
                    }

                # Handle single timer
                elif departure_datetime is not None:
                    if isinstance(departure_datetime, int):
                        dt = datetime.fromtimestamp(departure_datetime)
                    elif isinstance(departure_datetime, str):
                        dt = datetime.fromisoformat(departure_datetime)
                    else:
                        dt = departure_datetime

                    # Ensure timezone awareness using local timezone (non-blocking)
                    if dt.tzinfo is None:
                        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
                        dt = dt.replace(tzinfo=local_tz)

                    # Keep as local time - no UTC conversion
                    payload["singleTimer"] = {
                        "departureDateTimeLocal": dt.strftime("%Y-%m-%dT%H:%M:%S")
                    }

                # Build preferredChargingTimes (always included)
                payload["preferredChargingTimes"] = [
                    {
                        "id": 1,
                        "enabled": preferred_charging_times_enabled
                        if preferred_charging_times_enabled is not None
                        else False,
                        "startTimeLocal": preferred_charging_times_start_time.strftime(
                            "%H:%M"
                        )
                        if preferred_charging_times_start_time
                        else "00:00",
                        "endTimeLocal": preferred_charging_times_end_time.strftime(
                            "%H:%M"
                        )
                        if preferred_charging_times_end_time
                        else "00:00",
                    }
                ]

                _LOGGER.debug("Departure Timer payload: %s", payload)
                _LOGGER.debug("Updating Departure Timer %s", timer_id)
                if is_ev_timer:
                    raise HomeAssistantError(
                        f"Timer {timer_id} is an EV Departure timer."
                    )
                if is_aux_timer:
                    raise HomeAssistantError(
                        f"Timer {timer_id} is an Auxiliary/AC timer."
                    )
                result = await vehicle.update_departure_timer(
                    timer_id=timer_id, spin=spin, timer_data=payload
                )
                if result is False:
                    raise HomeAssistantError(
                        f"Failed to update departure timer {timer_id}"
                    )

            elif is_aux_timer:
                # Build auxiliary departure timer payload
                payload = {
                    "id": timer_id,
                    "enabled": enabled if enabled is not None else True,
                }

                # Handle recurring timer
                if frequency == "recurring" and departure_time is not None:
                    from datetime import time

                    if isinstance(departure_time, time):
                        time_str = departure_time.strftime("%H:%M")
                    else:
                        time_str = departure_time.strftime("%H:%M")

                    # Build repetitionDays array (lowercase day names)
                    weekday_map_plural = {
                        "Monday": "monday",
                        "Tuesday": "tuesday",
                        "Wednesday": "wednesday",
                        "Thursday": "thursday",
                        "Friday": "friday",
                        "Saturday": "saturday",
                        "Sunday": "sunday",
                    }

                    weekday_map_singular = {
                        "Monday": "monday",
                        "Tuesday": "tuesday",
                        "Wednesday": "wednesday",
                        "Thursday": "thursday",
                        "Friday": "friday",
                        "Saturday": "saturday",
                        "Sunday": "sunday",
                    }

                    recurring_on = {day: False for day in weekday_map_plural.values()}
                    repetition_days = []

                    if weekdays:
                        for day in weekdays:
                            if day in weekday_map_plural:
                                recurring_on[weekday_map_plural[day]] = True
                                repetition_days.append(weekday_map_singular[day])

                    payload["recurringTimer"] = {
                        "startTimeLocal": time_str,
                        "targetTimeLocal": time_str,
                        "recurringOn": recurring_on,
                        "repetitionDays": repetition_days,
                    }

                # Handle single timer
                elif departure_datetime is not None:
                    if isinstance(departure_datetime, int):
                        dt = datetime.fromtimestamp(departure_datetime)
                    elif isinstance(departure_datetime, str):
                        dt = datetime.fromisoformat(departure_datetime)
                    else:
                        dt = departure_datetime

                    # Ensure timezone awareness using local timezone (non-blocking)
                    if dt.tzinfo is None:
                        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
                        dt = dt.replace(tzinfo=local_tz)

                    # Keep as local time - no UTC conversion
                    dt_str = dt.strftime("%Y-%m-%dT%H:%M:%S")
                    payload["singleTimer"] = {
                        "startDateTimeLocal": dt_str,
                        "targetDateTimeLocal": dt_str,
                    }

                _LOGGER.debug("Auxiliary Departure Timer payload: %s", payload)
                _LOGGER.debug("Updating Auxiliary Departure Timer %s", timer_id)
                if is_ev_timer:
                    raise HomeAssistantError(
                        f"Timer {timer_id} is an EV Departure timer (has profile_id)."
                    )
                if is_departure_timer:
                    raise HomeAssistantError(f"Timer {timer_id} is a Departure timer.")
                result = await vehicle.update_departure_timer(
                    timer_id=timer_id, spin=spin, timer_data=payload
                )
                if result is False:
                    raise HomeAssistantError(
                        f"Failed to update auxiliary departure timer {timer_id}"
                    )

            else:
                raise HomeAssistantError("Unable to determine timer type")

            # Old code for reference - commented out
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

    def _validate_timer_parameters(
        self,
        is_departure_timer: bool,
        is_ev_timer: bool,
        is_aux_timer: bool,
        charging_profile: int | None,
        enabled: bool | None,
        charging: bool | None,
        climatisation: bool | None,
        frequency: str | None,
        departure_time,
        departure_datetime,
        weekdays: list | None,
        preferred_charging_times_enabled: bool | None,
        preferred_charging_times_start_time,
        preferred_charging_times_end_time,
    ) -> None:
        """Validate timer parameters based on timer type."""

        # enabled is always required
        if enabled is None:
            raise HomeAssistantError("enabled parameter is required")

        # EV Timer validation
        if is_ev_timer:
            # EV timer cannot have departure timer fields
            if charging_profile is None:
                raise HomeAssistantError(
                    "charging_profile is required for EV Departure timer"
                )
            if charging is not None:
                raise HomeAssistantError(
                    "charging parameter cannot be used with EV Departure timer"
                )
            if climatisation is not None:
                raise HomeAssistantError(
                    "climatisation parameter cannot be used with EV Departure timer"
                )
            if any(
                [
                    preferred_charging_times_enabled,
                    preferred_charging_times_start_time,
                    preferred_charging_times_end_time,
                ]
            ):
                raise HomeAssistantError(
                    "preferred_charging_times cannot be used with EV Departure timer"
                )

            # Frequency is required for EV timers
            if frequency not in ["recurring", "single"]:
                raise HomeAssistantError(
                    "EV Departure timer requires frequency parameter ('recurring' or 'single')"
                )

            # Check for correct parameters based on frequency
            if frequency == "recurring":
                if departure_time is None:
                    raise HomeAssistantError(
                        "departure_time is required for recurring EV Departure timer"
                    )
                if departure_datetime is not None:
                    raise HomeAssistantError(
                        "departure_datetime cannot be used with recurring timer (use departure_time)"
                    )
                # weekdays are optional for EV (defaults to all days)
            elif frequency == "single":
                if departure_datetime is None:
                    raise HomeAssistantError(
                        "departure_datetime is required for single EV Departure timer"
                    )
                if departure_time is not None:
                    raise HomeAssistantError(
                        "departure_time cannot be used with single timer (use departure_datetime)"
                    )

        # Departure Timer validation
        elif is_departure_timer:
            # Departure timer requires charging and climatisation parameters
            if charging is None:
                raise HomeAssistantError(
                    "charging parameter is required for departure timer"
                )
            if climatisation is None:
                raise HomeAssistantError(
                    "climatisation parameter is required for departure timer"
                )

            # Departure timer requires all preferred_charging_times parameters
            if preferred_charging_times_enabled is None:
                raise HomeAssistantError(
                    "preferred_charging_times_enabled is required for departure timer"
                )
            if preferred_charging_times_start_time is None:
                raise HomeAssistantError(
                    "preferred_charging_times_start_time is required for departure timer"
                )
            if preferred_charging_times_end_time is None:
                raise HomeAssistantError(
                    "preferred_charging_times_end_time is required for departure timer"
                )

            # Check for mixed parameters
            if frequency == "recurring":
                if departure_time is None:
                    raise HomeAssistantError(
                        "departure_time is required for recurring departure timer"
                    )
                if departure_datetime is not None:
                    raise HomeAssistantError(
                        "departure_datetime cannot be used with recurring timer (use departure_time)"
                    )
                # weekdays are required and cannot be empty for departure recurring
                if not weekdays or len(weekdays) == 0:
                    raise HomeAssistantError(
                        "weekdays parameter is required and cannot be empty for recurring departure timer"
                    )
            elif frequency == "single":
                if departure_datetime is None:
                    raise HomeAssistantError(
                        "departure_datetime is required for single departure timer"
                    )
                if departure_time is not None:
                    raise HomeAssistantError(
                        "departure_time cannot be used with single timer (use departure_datetime)"
                    )
            else:
                # No frequency specified - must have departure_datetime for single timer
                if departure_datetime is None and departure_time is None:
                    raise HomeAssistantError(
                        "Either departure_time (recurring) or departure_datetime (single) is required"
                    )
                if departure_datetime is not None and departure_time is not None:
                    raise HomeAssistantError(
                        "Cannot specify both departure_time and departure_datetime"
                    )
                # If departure_time without frequency, require weekdays
                if departure_time is not None and (not weekdays or len(weekdays) == 0):
                    raise HomeAssistantError(
                        "weekdays parameter is required and cannot be empty when using departure_time"
                    )

        # Auxiliary Timer validation
        elif is_aux_timer:
            # Auxiliary timer cannot have EV timer fields
            if charging_profile is not None:
                raise HomeAssistantError(
                    "charging_profile cannot be used with auxiliary timer"
                )
            # Auxiliary timer cannot have departure timer fields
            if charging is not None:
                raise HomeAssistantError(
                    "charging parameter cannot be used with auxiliary timer"
                )
            if climatisation is not None:
                raise HomeAssistantError(
                    "climatisation parameter cannot be used with auxiliary timer"
                )
            if any(
                [
                    preferred_charging_times_enabled,
                    preferred_charging_times_start_time,
                    preferred_charging_times_end_time,
                ]
            ):
                raise HomeAssistantError(
                    "preferred_charging_times cannot be used with auxiliary timer"
                )

            # Check for correct parameters based on frequency
            if frequency == "recurring":
                if departure_time is None:
                    raise HomeAssistantError(
                        "departure_time is required for recurring auxiliary timer"
                    )
                if departure_datetime is not None:
                    raise HomeAssistantError(
                        "departure_datetime cannot be used with recurring timer (use departure_time)"
                    )
                # weekdays are optional for auxiliary (defaults to all days)
            elif frequency == "single":
                if departure_datetime is None:
                    raise HomeAssistantError(
                        "departure_datetime is required for single auxiliary timer"
                    )
                if departure_time is not None:
                    raise HomeAssistantError(
                        "departure_time cannot be used with single timer (use departure_datetime)"
                    )
        else:
            raise HomeAssistantError("Unable to determine timer type")
