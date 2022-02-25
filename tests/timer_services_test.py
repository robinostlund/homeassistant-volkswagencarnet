"""Timer services tests."""
import asyncio
from asyncio import Future
from datetime import timedelta
from types import MappingProxyType
from unittest.mock import patch, MagicMock

import freezegun
import homeassistant.config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry
from homeassistant.util.unit_system import METRIC_SYSTEM
from volkswagencarnet.vw_timer import (
    TimerData,
    TimersAndProfiles,
    TimerProfileList,
    TimerProfile,
    Timer,
    TimerList,
    BasicSettings,
)
from volkswagencarnet.vw_vehicle import Vehicle

from custom_components.volkswagencarnet import (
    DOMAIN,
    SERVICE_SET_TIMER_BASIC_SETTINGS,
    VolkswagenCoordinator,
    CONF_VEHICLE,
    CONF_REGION,
    CONF_DEBUG,
    SERVICE_SET_TIMER_BASIC_SETTINGS_SCHEMA,
    SchedulerService,
)
from .hass_mocks import MockConfigEntry


async def test_get_coordinator(hass: HomeAssistant):
    """Test that we can find the coordinator."""
    dev_id: str = "xyz"
    service = SchedulerService(hass=hass)

    m_coord = MagicMock(VolkswagenCoordinator)
    config = {
        CONF_DEBUG: False,
        CONF_PASSWORD: "",
        CONF_USERNAME: "",
        CONF_VEHICLE: dev_id,
        CONF_REGION: "zz",
        "coordinator": m_coord,
    }

    # We want to skip the actual setup flow here
    with patch.object(homeassistant.config_entries.ConfigEntries, "async_setup") as flow, patch.object(
        homeassistant.config_entries.ConfigEntries, "_async_schedule_save"
    ):
        f: Future = Future()
        f.set_result(True)
        flow.return_value = f
        config_entry = MockConfigEntry(domain=DOMAIN, data=config)

        await hass.config_entries.async_add(config_entry)

    registry = device_registry.async_get(hass)

    identifiers: set[tuple[str, str]] = {tuple(["volkswagencarnet", dev_id])}  # type: ignore

    dev_entry = registry.async_get_or_create(config_entry_id=config_entry.entry_id, identifiers=identifiers)

    service_call = ServiceCall(
        DOMAIN,
        SERVICE_SET_TIMER_BASIC_SETTINGS,
        {
            "device_id": dev_entry.id,
        },
    )

    res = await SchedulerService.get_coordinator(self=service, service_call=service_call)
    assert m_coord == res


@patch("custom_components.volkswagencarnet.Connection")
async def test_call_service(conn: MagicMock, hass: HomeAssistant):
    """Test service call."""
    e = MockConfigEntry(
        data={CONF_VEHICLE: "xyz", CONF_USERNAME: "", CONF_PASSWORD: "", CONF_DEBUG: True, CONF_REGION: "ZZ"}
    )

    c: VolkswagenCoordinator = VolkswagenCoordinator(hass=hass, entry=e, update_interval=timedelta(minutes=10))
    c.connection.vehicles = [MagicMock(Vehicle)]
    c.connection.vehicles[0].vin = "XYZ"

    tmpdata = e.as_dict()["data"]
    tmpdata["coordinator"] = c
    e.data = MappingProxyType(tmpdata)

    s = SchedulerService(hass=hass)

    hass.services.async_register(
        domain=DOMAIN,
        service=SERVICE_SET_TIMER_BASIC_SETTINGS,
        service_func=s.set_timer_basic_settings,
        schema=SERVICE_SET_TIMER_BASIC_SETTINGS_SCHEMA,
    )

    assert hass.services.has_service(DOMAIN, SERVICE_SET_TIMER_BASIC_SETTINGS)

    hass.config.units = METRIC_SYSTEM
    target_temp = 24.5
    data = {"device_id": e.entry_id, "target_temperature": target_temp}

    with patch.object(s, "get_coordinator") as m, patch.object(c.connection, "getTimers") as get_timers:
        m.return_value = c
        timer_profiles = [
            TimerProfile(
                timestamp="2022-02-22T20:22:00Z",
                profileID="1",
                profileName="Unit test profile charge+clima",
                chargeMaxCurrent="5",
                targetChargeLevel="90",
                nightRateTimeStart="00:00",
                nightRateTimeEnd="",
                nightRateActive=False,
                operationClimatisation=True,
                operationCharging=True,
            )
        ]
        timer_list = [
            Timer(
                timestamp="2022-02-22T20:22:00Z",
                timerID="1",
                profileID="1",
                timerProgrammedStatus="programmed",
                timerFrequency="cyclic",
                departureWeekdayMask="nynnynn",
                departureDateTime="00:00",
                departureTimeOfDay="07:33",
            )
        ]
        basic_settings = BasicSettings(timestamp="2022-02-22T20:22:00Z", targetTemperature=2965, chargeMinLimit=20)
        tpl = TimerProfileList(timer_profiles)
        tp = TimersAndProfiles(timerProfileList=tpl, timerList=TimerList(timer_list), timerBasicSetting=basic_settings)

        future: Future = asyncio.Future()
        future.set_result(TimerData(timersAndProfiles=tp, status={}))
        get_timers.return_value = future

        res = await hass.services.async_call(
            domain=DOMAIN, service=SERVICE_SET_TIMER_BASIC_SETTINGS, service_data=data, blocking=True, limit=15
        )

        c.connection.vehicles[0].set_climatisation_temp.assert_called_once()
        used_args = c.connection.vehicles[0].set_climatisation_temp.call_args_list[0].args[0]
        # check that the correct VW temperature unit was set
        assert 2975 == used_args

    assert res is True


@freezegun.freeze_time("2022-02-22T12:20:22Z")
def test_time_to_utc(hass: HomeAssistant):
    """Test time conversion."""
    s = SchedulerService(hass=hass)

    with patch.object(hass.config, "time_zone", "America/Anchorage"):
        assert s.time_to_utc("16:00:34") == "01:00"

    with patch.object(hass.config, "time_zone", "Europe/Helsinki"):
        assert s.time_to_utc("15:00:34") == "13:00"


def test_validate_charge_amps():
    from custom_components.volkswagencarnet.services import validate_charge_max_current

    assert validate_charge_max_current(3) is False
    assert validate_charge_max_current(32) is True
    assert validate_charge_max_current("10") is True
    assert validate_charge_max_current("max") is True
    assert validate_charge_max_current("foo") is False