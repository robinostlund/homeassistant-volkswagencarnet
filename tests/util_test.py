"""Timer services tests."""

from asyncio import Future
from unittest.mock import patch, MagicMock

import freezegun
import homeassistant.config_entries
import pytest
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry

from custom_components.volkswagencarnet import (
    VolkswagenCoordinator,
    SchedulerService,
    util,
)
from custom_components.volkswagencarnet.const import (
    DOMAIN,
    CONF_VEHICLE,
    CONF_REGION,
    CONF_DEBUG,
)
from .hass_mocks import MockConfigEntry


async def test_get_coordinator(hass: HomeAssistant):
    """Test that we can find the coordinator."""
    dev_id: str = "xyz"

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
    with patch.object(
        homeassistant.config_entries.ConfigEntries, "async_setup"
    ) as flow, patch.object(
        homeassistant.config_entries.ConfigEntries, "_async_schedule_save"
    ):
        f: Future = Future()
        f.set_result(True)
        flow.return_value = f
        config_entry = MockConfigEntry(domain=DOMAIN, data=config)

        await hass.config_entries.async_add(config_entry)

    registry = device_registry.async_get(hass)

    identifiers: set[tuple[str, str]] = {tuple(["volkswagencarnet", dev_id])}  # type: ignore

    dev_entry = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id, identifiers=identifiers
    )

    res = await util.get_coordinator(hass=hass, config_entry=config_entry)
    assert m_coord == res


@freezegun.freeze_time("2022-02-22T12:20:22Z")
def test_time_to_utc(hass: HomeAssistant):
    """Test time conversion."""
    s = SchedulerService(hass=hass)

    with patch.object(hass.config, "time_zone", "America/Anchorage"):
        assert s.time_to_utc("16:00:34") == "01:00"

    with patch.object(hass.config, "time_zone", "Europe/Helsinki"):
        assert s.time_to_utc("15:00:34") == "13:00"


def test_validate_charge_amps():
    for v in [3, "foo"]:
        try:
            util.validate_charge_max_current(v)
            pytest.fail("Should have thrown exception")
        except ValueError:
            pass
    for v in [32, "10", "max"]:
        assert isinstance(util.validate_charge_max_current(v), int)
