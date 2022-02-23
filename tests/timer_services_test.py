import asyncio
from asyncio import Future
from datetime import timedelta
from unittest.mock import patch, MagicMock

import homeassistant.config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry
from homeassistant.loader import Integration
from volkswagencarnet.vw_timer import TimerData, TimerAndProfiles, TimerProfileList, TimerProfile, Timer, TimerList, \
    BasicSettings

from custom_components.volkswagencarnet import DOMAIN, SERVICE_SET_TIMER_BASIC_SETTINGS, VolkswagenCoordinator, \
    CONF_VEHICLE, CONF_REGION, CONF_DEBUG, SERVICE_SET_TIMER_BASIC_SETTINGS_SCHEMA, SchedulerService
from .hass_mocks import MockConfigEntry


async def test_get_coordinator(hass: HomeAssistant):
    dev_id: str = "xyz"
    service = SchedulerService(hass=hass)

    m_coord = MagicMock(VolkswagenCoordinator)
    config = {
        CONF_DEBUG: False,
        CONF_PASSWORD: '',
        CONF_USERNAME: '',
        CONF_VEHICLE: dev_id,
        CONF_REGION: 'zz',
        'coordinator': m_coord
    }

    # We want to skip the actual setup flow here
    with patch.object(homeassistant.config_entries.ConfigEntries, "async_setup") as flow, patch.object(homeassistant.config_entries.ConfigEntries, "_async_schedule_save"):
        f = Future()
        f.set_result(True)
        flow.return_value = f
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="foobar",
            data=config
        )

        # FIXME: make async_setup a mock that returns true
        await hass.config_entries. async_add(config_entry)

    registry = device_registry.async_get(hass)

    # noinspection PyTypeChecker
    identifiers: set[tuple[str, str]] = {tuple(['volkswagencarnet', dev_id])}

    dev_entry = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers=identifiers
    )

    service_call = ServiceCall(
        DOMAIN,
        SERVICE_SET_TIMER_BASIC_SETTINGS, {
        "device_id": dev_entry.id,
    })

    res = await SchedulerService.get_coordinator(self=service, service_call=service_call)
    assert m_coord == res


@patch("custom_components.volkswagencarnet.Connection")
async def test_call_service(conn: MagicMock, hass: HomeAssistant):
    e = MockConfigEntry(data={
        CONF_VEHICLE: "xyz",
        CONF_USERNAME: "",
        CONF_PASSWORD: "",
        CONF_DEBUG: True,
        CONF_REGION: "ZZ"
    }, unique_id="12345678901234567890123456789012")

    c: VolkswagenCoordinator = VolkswagenCoordinator(hass=hass, entry=e, update_interval=timedelta(minutes=10))

    s = SchedulerService(hass=hass)

    hass.services.async_register(
        domain=DOMAIN,
        service=SERVICE_SET_TIMER_BASIC_SETTINGS,
        service_func=s.set_timer_basic_settings,
        schema=SERVICE_SET_TIMER_BASIC_SETTINGS_SCHEMA
    )

    assert hass.services.has_service(DOMAIN, SERVICE_SET_TIMER_BASIC_SETTINGS)

    data = {
        "device_id": e.entry_id,
        "target_temperature_celsius": 24.5
    }

    with patch.object(s, "get_coordinator") as m,\
            patch.object(c.connection, "getTimers") as get_timers, \
            patch.object(c.connection, "setTimersAndProfiles") as set_timers:
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
                operationCharging=True
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
                departureTimeOfDay="07:33"
            )
        ]
        basic_settings = BasicSettings(
            timestamp="2022-02-22T20:22:00Z",
            targetTemperature=2965,
            chargeMinLimit=20
        )
        tpl = TimerProfileList(timer_profiles)
        tp = TimerAndProfiles(timerProfileList=tpl, timerList=TimerList(timer_list), timerBasicSetting=basic_settings)

        future = asyncio.Future()
        future.set_result(TimerData(timersAndProfiles=tp, status={}))
        get_timers.return_value = future

        res = await hass.services.async_call(
            domain=DOMAIN,
            service=SERVICE_SET_TIMER_BASIC_SETTINGS,
            service_data=data,
            blocking=True,
            limit=15
        )

        set_timers.assert_called_once()
        used_args = set_timers.call_args_list[0].args[0]
        assert isinstance(used_args, TimerData)
        # check that the correct VW temperature unit was set
        assert 2975 == used_args.timersAndProfiles.timerBasicSetting.targetTemperature

    assert res is True
