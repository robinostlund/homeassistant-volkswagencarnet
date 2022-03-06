from unittest.mock import patch, MagicMock

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from volkswagencarnet.vw_connection import Connection

from custom_components.volkswagencarnet import CONF_DEBUG, CONF_REGION, config_flow
from custom_components.volkswagencarnet.config_flow import VolkswagenCarnetConfigFlow


@patch("custom_components.volkswagencarnet.config_flow.Connection")
async def test_flow_user_init_auth_fails(m_connection, hass: HomeAssistant):
    """Test errors populated when login fails."""
    m_conn = MagicMock(Connection)
    # m_conn.doLogin = AsyncMock()
    m_conn.doLogin.side_effect = Exception

    _result: FlowResult = await hass.config_entries.flow.async_init(config_flow.DOMAIN, context={"source": "user"})

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        user_input={CONF_USERNAME: "unit tester", CONF_PASSWORD: "password123", CONF_DEBUG: True, CONF_REGION: "XX"},
    )

    flow: VolkswagenCarnetConfigFlow = hass.config_entries.flow._progress[result["flow_id"]]
    with patch.object(flow._connection, "doLogin") as aaaaa:
        aaaaa.side_effect = Exception

        result = await hass.config_entries.flow.async_configure(
            _result["flow_id"],
        )
    # Flow should go back to user details if login fails
    assert "user" == result["step_id"]
