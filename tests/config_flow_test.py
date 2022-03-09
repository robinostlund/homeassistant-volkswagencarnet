from unittest.mock import patch, MagicMock

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_RESOURCES,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from pytest_homeassistant_custom_component.common import MockConfigEntry
from volkswagencarnet.vw_connection import Connection
from volkswagencarnet.vw_dashboard import (
    Dashboard,
    Position,
    DoorLock,
    TrunkLock,
    RequestUpdate,
    WindowHeater,
    BatteryClimatisation,
)
from volkswagencarnet.vw_vehicle import Vehicle

from custom_components.volkswagencarnet import config_flow, VolkswagenCoordinator
from custom_components.volkswagencarnet.config_flow import VolkswagenCarnetConfigFlow
from custom_components.volkswagencarnet.const import (
    CONF_DEBUG,
    CONF_REGION,
    DOMAIN,
    CONF_CONVERT,
    CONF_REPORT_REQUEST,
    CONF_AVAILABLE_RESOURCES,
    CONF_IMPERIAL_UNITS,
)

DUMMY_CONFIG = {CONF_USERNAME: "unit tester", CONF_PASSWORD: "password123", CONF_DEBUG: True, CONF_REGION: "XX"}
DUMMY_OPTIONS = {CONF_CONVERT: CONF_IMPERIAL_UNITS, CONF_DEBUG: True, CONF_REGION: "XY", CONF_REPORT_REQUEST: False}


@patch("custom_components.volkswagencarnet.config_flow.Connection")
async def test_flow_user_init_auth_fails(m_connection, hass: HomeAssistant):
    """Test errors populated when login fails."""
    m_conn = MagicMock(Connection)
    # m_conn.doLogin = AsyncMock()
    m_conn.doLogin.side_effect = Exception

    _result: FlowResult = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        user_input=DUMMY_CONFIG,
    )

    flow: VolkswagenCarnetConfigFlow = hass.config_entries.flow._progress[result["flow_id"]]
    with patch.object(flow._connection, "doLogin") as aaaaa:
        aaaaa.side_effect = Exception

        result = await hass.config_entries.flow.async_configure(
            _result["flow_id"],
        )
    # Flow should go back to user details if login fails
    assert "user" == result["step_id"]


@patch("custom_components.volkswagencarnet.config_flow.get_coordinator")
@patch("custom_components.volkswagencarnet.config_flow.get_vehicle")
async def test_options_flow(get_vehicle: MagicMock, get_coordinator: MagicMock, hass: HomeAssistant, m_connection):
    """Test options flow."""
    m_dashboard = MagicMock(spec=Dashboard)
    m_dashboard.instruments = [
        Position(),
        DoorLock(),
        TrunkLock(),
        RequestUpdate(),
        WindowHeater(),
        BatteryClimatisation(),
    ]

    vehicle: Vehicle = MagicMock(spec=Vehicle)
    vehicle.is_position_supported.return_value = True
    vehicle.is_climatisation_without_external_power_supported.return_value = True
    vehicle.dashboard.return_value = m_dashboard

    m_coordinator = MagicMock(VolkswagenCoordinator)

    get_vehicle.return_value = vehicle
    get_coordinator.return_value = m_coordinator

    # Create a new MockConfigEntry and add to HASS (bypassing config flow)
    entry = MockConfigEntry(
        domain=DOMAIN,
        # data={**DUMMY_CONFIG, **{"coordinator": m_coordinator}},
        data=DUMMY_CONFIG,
        options={"resources": {}, "unknown_stuff": "foobar"},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Verify that the first options step is a user form
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    # Enter the same dummy data just to get the next step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=DUMMY_OPTIONS,
    )

    # Verify that the options step is a instrument selection form
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "select_instruments"
    assert result["last_step"] is True

    new_resources = ["position"]
    # Select some instruments
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_RESOURCES: new_resources}
    )

    # Verify that the flow finishes
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == ""

    # Verify that the options were updated
    assert entry.options.get(CONF_RESOURCES) == new_resources
    # but nothing unknown was destroyed
    assert entry.options.get("unknown_stuff") == "foobar"
    # and we have something in "all resources"
    assert entry.options.get(CONF_AVAILABLE_RESOURCES, None) is not None
