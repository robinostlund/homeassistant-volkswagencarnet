"""Utility tests."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.volkswagencarnet import (
    VolkswagenCoordinator,
    util,
)
from custom_components.volkswagencarnet.const import (
    DATA,
    DOMAIN,
    CONF_VEHICLE,
    CONF_REGION,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_get_coordinator(hass: HomeAssistant):
    """Test that we can find the coordinator."""
    m_coord = MagicMock(VolkswagenCoordinator)

    mock_data = MagicMock()
    mock_data.coordinator = m_coord

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_VEHICLE: "xyz",
            CONF_REGION: "zz",
        },
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {DATA: mock_data}

    res = await util.get_coordinator(hass=hass, config_entry=config_entry)
    assert res is m_coord
