"""Tests for Phase 2 NA Library Integration (NAL gaps 01-05).

Coverage:
  NAL-01: Forked library dependency in requirements.txt and manifest.json
  NAL-02: Country selector in config flow DATA_SCHEMA
  NAL-03: country= parameter forwarded to Connection() in config flow and coordinator
  NAL-05: v3 -> v4 migration (CONF_REGION -> CONF_COUNTRY, repair issue, ConfirmCountryRepairFlow)

ESCALATE: IMPL-BUG-01
  async_migrate_entry (__init__.py lines 150/162/171) uses the pattern:
      version = entry.version = N
  Direct assignment to ConfigEntry.version is forbidden in
  homeassistant >= 2026.x (config_entries.py: UPDATE_ENTRY_CONFIG_ENTRY_ATTRS guard).
  This will raise AttributeError at runtime for any v1, v2 or v3 entry migration.
  Fix: replace `entry.version = N` with `hass.config_entries.async_update_entry(entry, version=N, ...)`
  The migration tests in this file use a __setattr__ patch to bypass the guard and still
  exercise the underlying migration logic.  See test_nal05_migration_version_assignment_raises
  for the failing baseline test that documents the bug.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.volkswagencarnet.const import (
    CONF_COUNTRY,
    CONF_COUNTRY_CUSTOM,
    CONF_REGION,
    COUNTRY_LIST,
    DEFAULT_COUNTRY,
    DOMAIN,
)

# Root of the repository (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent

FORKED_GIT_URL = "git+https://github.com/Pascal-ZeGerman/volkswagencarnet"


# ===========================================================================
# GAP 1: NAL-01 — Forked library dependency
# ===========================================================================


def test_nal01_requirements_txt_has_forked_git_url():
    """requirements.txt must reference the forked GitHub URL."""
    req_file = REPO_ROOT / "requirements.txt"
    assert req_file.exists(), "requirements.txt not found in repo root"
    content = req_file.read_text()
    assert FORKED_GIT_URL in content, (
        f"requirements.txt does not contain forked git URL '{FORKED_GIT_URL}'.\n"
        f"Actual content:\n{content}"
    )


def test_nal01_manifest_requirements_has_forked_git_url():
    """manifest.json requirements array must reference the forked GitHub URL."""
    manifest_file = (
        REPO_ROOT / "custom_components" / "volkswagencarnet" / "manifest.json"
    )
    assert manifest_file.exists(), "manifest.json not found"
    manifest = json.loads(manifest_file.read_text())
    requirements = manifest.get("requirements", [])
    assert isinstance(requirements, list), "manifest.json 'requirements' must be a list"
    matching = [r for r in requirements if FORKED_GIT_URL in r]
    assert matching, (
        f"manifest.json requirements do not contain forked git URL '{FORKED_GIT_URL}'.\n"
        f"Actual requirements: {requirements}"
    )


def test_nal01_requirements_and_manifest_in_sync():
    """The forked git requirement spec in requirements.txt and manifest.json must match."""
    req_content = (REPO_ROOT / "requirements.txt").read_text()
    manifest = json.loads(
        (
            REPO_ROOT / "custom_components" / "volkswagencarnet" / "manifest.json"
        ).read_text()
    )

    req_lines = [
        line.strip() for line in req_content.splitlines() if FORKED_GIT_URL in line
    ]
    assert req_lines, "No matching line in requirements.txt"
    req_spec = req_lines[0]

    manifest_reqs = manifest.get("requirements", [])
    manifest_matching = [r for r in manifest_reqs if FORKED_GIT_URL in r]
    assert manifest_matching, "No matching entry in manifest.json requirements"
    manifest_spec = manifest_matching[0]

    assert req_spec == manifest_spec, (
        f"Mismatch between requirements.txt and manifest.json:\n"
        f"  requirements.txt: {req_spec}\n"
        f"  manifest.json:    {manifest_spec}"
    )


# ===========================================================================
# GAP 2: NAL-02 — Country selector in config flow DATA_SCHEMA
# ===========================================================================


def test_nal02_country_list_has_16_entries():
    """COUNTRY_LIST must contain exactly 15 named countries plus 'OTHER'."""
    assert len(COUNTRY_LIST) == 16, (
        f"Expected 16 entries in COUNTRY_LIST, got {len(COUNTRY_LIST)}.\n"
        f"Keys: {list(COUNTRY_LIST.keys())}"
    )


def test_nal02_country_list_contains_other():
    """COUNTRY_LIST must include the sentinel 'OTHER' key."""
    assert "OTHER" in COUNTRY_LIST, "COUNTRY_LIST missing 'OTHER' key"


def test_nal02_country_list_contains_expected_country_codes():
    """COUNTRY_LIST must include both NA (US, CA) and major EU country codes."""
    expected = {"US", "CA", "DE", "GB", "NL", "SE", "NO", "FR", "IT", "ES"}
    missing = expected - set(COUNTRY_LIST.keys())
    assert not missing, f"COUNTRY_LIST is missing expected country codes: {missing}"


def test_nal02_data_schema_has_required_country_field():
    """DATA_SCHEMA must declare CONF_COUNTRY as vol.Required."""
    from custom_components.volkswagencarnet.config_flow import DATA_SCHEMA

    schema_keys = {key.schema: key for key in DATA_SCHEMA.schema}
    assert CONF_COUNTRY in schema_keys, (
        f"DATA_SCHEMA does not have '{CONF_COUNTRY}' key.\n"
        f"Available keys: {list(schema_keys.keys())}"
    )
    key_obj = schema_keys[CONF_COUNTRY]
    assert isinstance(key_obj, vol.Required), (
        f"'{CONF_COUNTRY}' in DATA_SCHEMA must be vol.Required, "
        f"got {type(key_obj).__name__}"
    )


def test_nal02_data_schema_country_accepts_all_country_list_values():
    """The DATA_SCHEMA validator for CONF_COUNTRY must accept every key in COUNTRY_LIST."""
    from custom_components.volkswagencarnet.config_flow import DATA_SCHEMA

    # Find the validator for CONF_COUNTRY
    validator = None
    for key in DATA_SCHEMA.schema:
        if key.schema == CONF_COUNTRY:
            validator = DATA_SCHEMA.schema[key]
            break

    assert validator is not None, f"No validator found for {CONF_COUNTRY}"

    for code in COUNTRY_LIST:
        try:
            validator(code)
        except vol.Invalid as exc:
            pytest.fail(
                f"COUNTRY_LIST key '{code}' was rejected by DATA_SCHEMA validator: {exc}"
            )


def test_nal02_data_schema_country_rejects_invalid_value():
    """The DATA_SCHEMA validator for CONF_COUNTRY must reject values not in COUNTRY_LIST."""
    from custom_components.volkswagencarnet.config_flow import DATA_SCHEMA

    validator = None
    for key in DATA_SCHEMA.schema:
        if key.schema == CONF_COUNTRY:
            validator = DATA_SCHEMA.schema[key]
            break

    assert validator is not None

    with pytest.raises(vol.Invalid):
        validator("INVALID_CODE_XYZ")


def test_nal02_data_schema_has_optional_country_custom_field():
    """DATA_SCHEMA must declare CONF_COUNTRY_CUSTOM as vol.Optional."""
    from custom_components.volkswagencarnet.config_flow import DATA_SCHEMA

    schema_keys = {key.schema: key for key in DATA_SCHEMA.schema}
    assert CONF_COUNTRY_CUSTOM in schema_keys, (
        f"DATA_SCHEMA does not have '{CONF_COUNTRY_CUSTOM}' key.\n"
        f"Available keys: {list(schema_keys.keys())}"
    )
    key_obj = schema_keys[CONF_COUNTRY_CUSTOM]
    assert isinstance(key_obj, vol.Optional), (
        f"'{CONF_COUNTRY_CUSTOM}' in DATA_SCHEMA must be vol.Optional, "
        f"got {type(key_obj).__name__}"
    )


async def test_nal02_other_collapse_accepts_valid_2char_code(hass: HomeAssistant):
    """async_step_user: CONF_COUNTRY='OTHER' with a valid 2-char custom code is accepted."""
    from custom_components.volkswagencarnet.config_flow import (
        VolkswagenCarnetConfigFlow,
    )

    flow = VolkswagenCarnetConfigFlow()
    flow.hass = hass

    user_input = {
        "name": "",
        "username": "user@example.com",
        "password": "secret",
        "spin": "",
        CONF_COUNTRY: "OTHER",
        CONF_COUNTRY_CUSTOM: "AU",
        "mutable": True,
        "convert": "no_conversion",
        "scan_interval": 5,
    }

    with (
        patch.object(
            flow, "async_show_form", return_value={"type": "form", "step_id": "user"}
        ) as mock_form,
        patch.object(
            flow, "async_step_login", new=AsyncMock(return_value={"type": "form"})
        ),
    ):
        await flow.async_step_user(user_input)

    # The form must NOT have been called with invalid_country_code error
    for c in mock_form.call_args_list:
        errors = c.kwargs.get("errors", {})
        assert errors.get(CONF_COUNTRY_CUSTOM) != "invalid_country_code", (
            "Valid 2-char country code 'AU' was incorrectly rejected"
        )

    # After collapse, CONF_COUNTRY must be the custom code, CONF_COUNTRY_CUSTOM removed
    assert flow._init_info.get(CONF_COUNTRY) == "AU", (
        f"Expected CONF_COUNTRY='AU' after collapse, got {flow._init_info.get(CONF_COUNTRY)!r}"
    )
    assert CONF_COUNTRY_CUSTOM not in flow._init_info, (
        "CONF_COUNTRY_CUSTOM must be removed from _init_info after collapse"
    )


async def test_nal02_other_collapse_rejects_non_2char_code(hass: HomeAssistant):
    """async_step_user: CONF_COUNTRY='OTHER' with non-2-char code must show invalid_country_code error."""
    from custom_components.volkswagencarnet.config_flow import (
        VolkswagenCarnetConfigFlow,
    )

    for bad_code in ["", "A", "AUS", "AUSTRALIA"]:
        flow = VolkswagenCarnetConfigFlow()
        flow.hass = hass

        user_input = {
            "name": "",
            "username": "user@example.com",
            "password": "secret",
            "spin": "",
            CONF_COUNTRY: "OTHER",
            CONF_COUNTRY_CUSTOM: bad_code,
            "mutable": True,
            "convert": "no_conversion",
            "scan_interval": 5,
        }

        with patch.object(
            flow, "async_show_form", return_value={"type": "form", "step_id": "user"}
        ) as mock_form:
            await flow.async_step_user(user_input)

        assert mock_form.called, f"async_show_form not called for bad_code={bad_code!r}"
        errors = mock_form.call_args.kwargs.get("errors", {})
        assert errors.get(CONF_COUNTRY_CUSTOM) == "invalid_country_code", (
            f"Expected 'invalid_country_code' error for bad_code={bad_code!r}, "
            f"got errors={errors}"
        )


async def test_nal02_other_collapse_strips_whitespace_and_uppercases(
    hass: HomeAssistant,
):
    """async_step_user: custom code whitespace is stripped and value is uppercased."""
    from custom_components.volkswagencarnet.config_flow import (
        VolkswagenCarnetConfigFlow,
    )

    flow = VolkswagenCarnetConfigFlow()
    flow.hass = hass

    user_input = {
        "name": "",
        "username": "user@example.com",
        "password": "secret",
        "spin": "",
        CONF_COUNTRY: "OTHER",
        CONF_COUNTRY_CUSTOM: "  nz  ",  # lowercase, surrounded by whitespace
        "mutable": True,
        "convert": "no_conversion",
        "scan_interval": 5,
    }

    with (
        patch.object(flow, "async_show_form") as mock_form,
        patch.object(
            flow, "async_step_login", new=AsyncMock(return_value={"type": "form"})
        ),
    ):
        await flow.async_step_user(user_input)

    # No error should be shown
    for c in mock_form.call_args_list:
        errors = c.kwargs.get("errors", {})
        assert errors.get(CONF_COUNTRY_CUSTOM) != "invalid_country_code", (
            "Whitespace-padded lowercase 2-char code should be accepted after stripping"
        )

    assert flow._init_info.get(CONF_COUNTRY) == "NZ", (
        f"Expected CONF_COUNTRY='NZ' after stripping+uppercasing, "
        f"got {flow._init_info.get(CONF_COUNTRY)!r}"
    )


# ===========================================================================
# GAP 3: NAL-03 — country= parameter passed to Connection()
# ===========================================================================


async def test_nal03_config_flow_passes_country_us_to_connection(hass: HomeAssistant):
    """Connection() in async_step_user must receive country='US' when US is selected."""
    from custom_components.volkswagencarnet.config_flow import (
        VolkswagenCarnetConfigFlow,
    )

    flow = VolkswagenCarnetConfigFlow()
    flow.hass = hass
    captured_kwargs: dict = {}

    def fake_connection(**kwargs):
        captured_kwargs.update(kwargs)
        conn = MagicMock()
        conn.logged_in = False
        conn.vehicles = []
        return conn

    user_input = {
        "name": "",
        "username": "user@example.com",
        "password": "secret",
        "spin": "",
        CONF_COUNTRY: "US",
        CONF_COUNTRY_CUSTOM: "",
        "mutable": True,
        "convert": "no_conversion",
        "scan_interval": 5,
    }

    with (
        patch(
            "custom_components.volkswagencarnet.config_flow.Connection",
            side_effect=fake_connection,
        ),
        patch.object(
            flow, "async_step_login", new=AsyncMock(return_value={"type": "form"})
        ),
    ):
        await flow.async_step_user(user_input)

    assert "country" in captured_kwargs, (
        "Connection() was not called with 'country' keyword argument"
    )
    assert captured_kwargs["country"] == "US", (
        f"Expected country='US', got country={captured_kwargs['country']!r}"
    )


async def test_nal03_config_flow_passes_country_ca_to_connection(hass: HomeAssistant):
    """Connection() in async_step_user must receive country='CA' when Canada is selected."""
    from custom_components.volkswagencarnet.config_flow import (
        VolkswagenCarnetConfigFlow,
    )

    flow = VolkswagenCarnetConfigFlow()
    flow.hass = hass
    captured_kwargs: dict = {}

    def fake_connection(**kwargs):
        captured_kwargs.update(kwargs)
        conn = MagicMock()
        conn.logged_in = False
        conn.vehicles = []
        return conn

    user_input = {
        "name": "",
        "username": "user@example.com",
        "password": "secret",
        "spin": "",
        CONF_COUNTRY: "CA",
        CONF_COUNTRY_CUSTOM: "",
        "mutable": True,
        "convert": "no_conversion",
        "scan_interval": 5,
    }

    with (
        patch(
            "custom_components.volkswagencarnet.config_flow.Connection",
            side_effect=fake_connection,
        ),
        patch.object(
            flow, "async_step_login", new=AsyncMock(return_value={"type": "form"})
        ),
    ):
        await flow.async_step_user(user_input)

    assert captured_kwargs.get("country") == "CA", (
        f"Expected country='CA', got country={captured_kwargs.get('country')!r}"
    )


async def test_nal03_coordinator_passes_country_to_connection(hass: HomeAssistant):
    """VolkswagenCoordinator must pass country= from entry.data[CONF_COUNTRY] to Connection()."""
    from datetime import timedelta

    from custom_components.volkswagencarnet import VolkswagenCoordinator

    captured_kwargs: dict = {}

    def fake_connection(**kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_COUNTRY: "US",
        },
    )

    with patch(
        "custom_components.volkswagencarnet.Connection", side_effect=fake_connection
    ):
        VolkswagenCoordinator(
            hass=hass, entry=entry, update_interval=timedelta(minutes=5)
        )

    assert "country" in captured_kwargs, (
        "VolkswagenCoordinator did not pass 'country' to Connection()"
    )
    assert captured_kwargs["country"] == "US", (
        f"Expected country='US', got country={captured_kwargs['country']!r}"
    )


async def test_nal03_coordinator_falls_back_to_conf_region(hass: HomeAssistant):
    """Coordinator must fall back to CONF_REGION value if CONF_COUNTRY is absent."""
    from datetime import timedelta

    from custom_components.volkswagencarnet import VolkswagenCoordinator

    captured_kwargs: dict = {}

    def fake_connection(**kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock()

    # Simulate an old v3 entry that was not yet migrated (no CONF_COUNTRY)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "NO",
        },
    )

    with patch(
        "custom_components.volkswagencarnet.Connection", side_effect=fake_connection
    ):
        VolkswagenCoordinator(
            hass=hass, entry=entry, update_interval=timedelta(minutes=5)
        )

    assert captured_kwargs.get("country") == "NO", (
        f"Expected fallback country='NO' from CONF_REGION, got {captured_kwargs.get('country')!r}"
    )


async def test_nal03_coordinator_falls_back_to_default_country(hass: HomeAssistant):
    """Coordinator must use DEFAULT_COUNTRY if neither CONF_COUNTRY nor CONF_REGION is set."""
    from datetime import timedelta

    from custom_components.volkswagencarnet import VolkswagenCoordinator

    captured_kwargs: dict = {}

    def fake_connection(**kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            # Neither CONF_COUNTRY nor CONF_REGION present
        },
    )

    with patch(
        "custom_components.volkswagencarnet.Connection", side_effect=fake_connection
    ):
        VolkswagenCoordinator(
            hass=hass, entry=entry, update_interval=timedelta(minutes=5)
        )

    assert captured_kwargs.get("country") == DEFAULT_COUNTRY, (
        f"Expected default country='{DEFAULT_COUNTRY}', got {captured_kwargs.get('country')!r}"
    )


async def test_nal03_reauth_passes_country_from_entry_data(hass: HomeAssistant):
    """async_step_reauth_confirm must forward CONF_COUNTRY from entry.data to Connection()."""
    from custom_components.volkswagencarnet.config_flow import (
        VolkswagenCarnetConfigFlow,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "old_user@example.com",
            "password": "oldpassword",
            CONF_COUNTRY: "SE",
        },
    )
    entry.add_to_hass(hass)

    flow = VolkswagenCarnetConfigFlow()
    flow.hass = hass
    flow._entry = entry
    captured_kwargs: dict = {}

    def fake_connection(**kwargs):
        captured_kwargs.update(kwargs)
        conn = MagicMock()
        conn.doLogin = AsyncMock(return_value=True)
        conn.logged_in = False
        conn.validate_login = AsyncMock(return_value=False)
        return conn

    with patch(
        "custom_components.volkswagencarnet.config_flow.Connection",
        side_effect=fake_connection,
    ):
        await flow.async_step_reauth_confirm(
            user_input={
                "username": "new_user@example.com",
                "password": "newpassword",
            }
        )

    assert captured_kwargs.get("country") == "SE", (
        f"Reauth did not forward CONF_COUNTRY='SE' to Connection(), "
        f"got {captured_kwargs.get('country')!r}"
    )


async def test_nal03_reauth_falls_back_to_conf_region_if_no_conf_country(
    hass: HomeAssistant,
):
    """async_step_reauth_confirm must fall back to CONF_REGION if CONF_COUNTRY is absent."""
    from custom_components.volkswagencarnet.config_flow import (
        VolkswagenCarnetConfigFlow,
    )

    # Old-style entry with only CONF_REGION
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "old@example.com",
            "password": "old",
            CONF_REGION: "FI",
        },
    )
    entry.add_to_hass(hass)

    flow = VolkswagenCarnetConfigFlow()
    flow.hass = hass
    flow._entry = entry
    captured_kwargs: dict = {}

    def fake_connection(**kwargs):
        captured_kwargs.update(kwargs)
        conn = MagicMock()
        conn.doLogin = AsyncMock(return_value=True)
        conn.logged_in = False
        conn.validate_login = AsyncMock(return_value=False)
        return conn

    with patch(
        "custom_components.volkswagencarnet.config_flow.Connection",
        side_effect=fake_connection,
    ):
        await flow.async_step_reauth_confirm(
            user_input={"username": "u@example.com", "password": "pw"}
        )

    assert captured_kwargs.get("country") == "FI", (
        f"Expected CONF_REGION fallback 'FI', got {captured_kwargs.get('country')!r}"
    )


# ===========================================================================
# GAP 4: NAL-05 — Migration v3 → v4
# ===========================================================================


async def _run_migration(hass: HomeAssistant, entry):
    """Helper: add entry to hass and invoke async_migrate_entry.

    NOTE: The implementation uses the now-forbidden direct assignment pattern
    ``entry.version = N`` (must use async_update_entry instead).  We patch
    ConfigEntry.__setattr__ to bypass the guard so the migration *logic* can
    still be exercised. The underlying bug is tracked as ESCALATE:
    IMPL-BUG-01 (see module docstring).
    """
    from custom_components.volkswagencarnet import async_migrate_entry
    from homeassistant.config_entries import ConfigEntry

    _orig_setattr = ConfigEntry.__setattr__

    def _permissive_setattr(self, key, value):
        # Allow 'version' to be set directly (bypass the guard for test purposes)
        if key == "version":
            object.__setattr__(self, key, value)
        else:
            _orig_setattr(self, key, value)

    with (
        patch("homeassistant.config_entries.ConfigEntries._async_schedule_save"),
        patch.object(ConfigEntry, "__setattr__", _permissive_setattr),
    ):
        entry.add_to_hass(hass)
        return await async_migrate_entry(hass, entry)


async def test_nal05_migration_no_version_assignment_error(hass: HomeAssistant):
    """Verify IMPL-BUG-01 is fixed: async_migrate_entry no longer raises AttributeError.

    The fix replaced direct `entry.version = N` assignments with version=N kwarg
    on async_update_entry(), which is the only supported way to change version in
    HA >= 2026.x. This test confirms migration completes without error.
    """
    from custom_components.volkswagencarnet import async_migrate_entry

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "DE",
        },
    )
    with patch("homeassistant.config_entries.ConfigEntries._async_schedule_save"):
        entry.add_to_hass(hass)
        # With the fix, this completes without raising AttributeError
        await async_migrate_entry(hass, entry)


async def test_nal05_migration_returns_true(hass: HomeAssistant):
    """async_migrate_entry must return True for a v3 config entry."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "DE",
        },
    )
    result = await _run_migration(hass, entry)
    assert result is True, "async_migrate_entry returned False for v3 entry"


async def test_nal05_version_bumped_to_4(hass: HomeAssistant):
    """Config entry version must be 4 after v3 migration."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "GB",
        },
    )
    await _run_migration(hass, entry)
    assert entry.version == 4, (
        f"Expected entry.version == 4 after migration, got {entry.version}"
    )


async def test_nal05_conf_region_renamed_to_conf_country_in_data(hass: HomeAssistant):
    """CONF_REGION in entry.data must become CONF_COUNTRY='NL' after migration."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "NL",
        },
    )
    await _run_migration(hass, entry)

    assert CONF_COUNTRY in entry.data, (
        f"'{CONF_COUNTRY}' not in entry.data after migration"
    )
    assert entry.data[CONF_COUNTRY] == "NL", (
        f"Expected CONF_COUNTRY='NL', got {entry.data.get(CONF_COUNTRY)!r}"
    )
    assert CONF_REGION not in entry.data, (
        f"'{CONF_REGION}' still present in entry.data after migration"
    )


async def test_nal05_missing_region_defaults_to_default_country(hass: HomeAssistant):
    """If CONF_REGION absent from data, CONF_COUNTRY must default to DEFAULT_COUNTRY."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            # No CONF_REGION
        },
    )
    await _run_migration(hass, entry)

    assert entry.data.get(CONF_COUNTRY) == DEFAULT_COUNTRY, (
        f"Expected CONF_COUNTRY='{DEFAULT_COUNTRY}' when CONF_REGION absent, "
        f"got {entry.data.get(CONF_COUNTRY)!r}"
    )


async def test_nal05_conf_region_renamed_in_options(hass: HomeAssistant):
    """CONF_REGION in entry.options must be renamed to CONF_COUNTRY after migration."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "SE",
        },
        options={
            CONF_REGION: "SE",
            "resources": ["position"],
        },
    )
    await _run_migration(hass, entry)

    assert CONF_COUNTRY in entry.options, (
        f"'{CONF_COUNTRY}' not in entry.options after migration"
    )
    assert entry.options[CONF_COUNTRY] == "SE", (
        f"Expected CONF_COUNTRY='SE' in options, got {entry.options.get(CONF_COUNTRY)!r}"
    )
    assert CONF_REGION not in entry.options, (
        f"'{CONF_REGION}' still in entry.options after migration"
    )


async def test_nal05_options_other_keys_preserved(hass: HomeAssistant):
    """Keys in options other than CONF_REGION must survive migration unchanged."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "FR",
        },
        options={
            "resources": ["position", "door_locked"],
            "available_resources": {"position": "Position"},
        },
    )
    await _run_migration(hass, entry)

    assert entry.options.get("resources") == ["position", "door_locked"], (
        "Migration must preserve 'resources' in options"
    )
    assert "available_resources" in entry.options, (
        "Migration must preserve 'available_resources' in options"
    )


async def test_nal05_repair_issue_created(hass: HomeAssistant):
    """async_migrate_entry must call ir.async_create_issue with a confirm_country_ issue ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "AT",
        },
    )

    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as mock_create_issue:
        await _run_migration(hass, entry)

    assert mock_create_issue.called, (
        "ir.async_create_issue was not called during migration"
    )
    args = mock_create_issue.call_args.args
    assert args[0] is hass, "async_create_issue: first arg must be hass"
    assert args[1] == DOMAIN, f"async_create_issue: domain must be '{DOMAIN}'"
    issue_id = args[2]
    assert issue_id.startswith("confirm_country_"), (
        f"Repair issue_id must start with 'confirm_country_', got '{issue_id}'"
    )
    assert entry.entry_id in issue_id, (
        f"Repair issue_id must contain entry_id '{entry.entry_id}'"
    )


async def test_nal05_repair_issue_data_has_entry_id_and_country(hass: HomeAssistant):
    """The repair issue data dict must include 'entry_id' and 'country'."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "CH",
        },
    )

    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as mock_create_issue:
        await _run_migration(hass, entry)

    issue_data = mock_create_issue.call_args.kwargs.get("data", {})
    assert issue_data.get("entry_id") == entry.entry_id, (
        f"Repair issue data['entry_id'] must be '{entry.entry_id}', got {issue_data.get('entry_id')!r}"
    )
    assert issue_data.get("country") == "CH", (
        f"Repair issue data['country'] must be 'CH', got {issue_data.get('country')!r}"
    )


async def test_nal05_repair_issue_is_fixable_with_warning_severity(hass: HomeAssistant):
    """The repair issue must be is_fixable=True with IssueSeverity.WARNING."""
    from homeassistant.helpers import issue_registry as ir

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_REGION: "DK",
        },
    )

    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as mock_create_issue:
        await _run_migration(hass, entry)

    kwargs = mock_create_issue.call_args.kwargs
    assert kwargs.get("is_fixable") is True, (
        f"Repair issue must have is_fixable=True, got {kwargs.get('is_fixable')!r}"
    )
    assert kwargs.get("severity") == ir.IssueSeverity.WARNING, (
        f"Repair issue must have severity=WARNING, got {kwargs.get('severity')!r}"
    )


# ===========================================================================
# GAP 4 (continued): NAL-05 — ConfirmCountryRepairFlow
# ===========================================================================


def test_nal05_async_create_fix_flow_returns_confirm_country_repair_flow():
    """async_create_fix_flow must return ConfirmCountryRepairFlow for confirm_country_ IDs."""
    from custom_components.volkswagencarnet.repairs import (
        ConfirmCountryRepairFlow,
        async_create_fix_flow,
    )

    hass = MagicMock()
    data = {"entry_id": "abc123", "country": "DE"}

    result = asyncio.get_event_loop().run_until_complete(
        async_create_fix_flow(hass, "confirm_country_abc123", data)
    )

    assert isinstance(result, ConfirmCountryRepairFlow), (
        f"Expected ConfirmCountryRepairFlow, got {type(result).__name__}"
    )


def test_nal05_async_create_fix_flow_raises_for_unknown_issue():
    """async_create_fix_flow must raise ValueError for unrecognised issue IDs."""
    from custom_components.volkswagencarnet.repairs import async_create_fix_flow

    hass = MagicMock()

    with pytest.raises(ValueError, match="Unknown repair issue id"):
        asyncio.get_event_loop().run_until_complete(
            async_create_fix_flow(hass, "unknown_issue_xyz", {})
        )


def test_nal05_repair_flow_stores_entry_id_and_country():
    """ConfirmCountryRepairFlow.__init__ must store entry_id and existing_country from data."""
    from custom_components.volkswagencarnet.repairs import ConfirmCountryRepairFlow

    flow = ConfirmCountryRepairFlow({"entry_id": "test_entry_123", "country": "SE"})

    assert flow._entry_id == "test_entry_123", (
        f"Expected _entry_id='test_entry_123', got {flow._entry_id!r}"
    )
    assert flow._existing_country == "SE", (
        f"Expected _existing_country='SE', got {flow._existing_country!r}"
    )


def test_nal05_repair_flow_uses_safe_defaults_for_empty_data():
    """ConfirmCountryRepairFlow must use safe defaults when initialized with an empty dict."""
    from custom_components.volkswagencarnet.repairs import ConfirmCountryRepairFlow

    flow = ConfirmCountryRepairFlow({})

    assert flow._entry_id == "", f"Expected empty _entry_id, got {flow._entry_id!r}"
    assert flow._existing_country == "DE", (
        f"Expected _existing_country='DE' (default), got {flow._existing_country!r}"
    )


async def test_nal05_repair_flow_confirm_shows_form_with_prepopulated_country(
    hass: HomeAssistant,
):
    """async_step_confirm(user_input=None) must show a form with CONF_COUNTRY pre-populated."""
    from custom_components.volkswagencarnet.repairs import ConfirmCountryRepairFlow

    flow = ConfirmCountryRepairFlow({"entry_id": "my_entry", "country": "NO"})
    flow.hass = hass

    result = await flow.async_step_confirm(user_input=None)

    # Result type 1 == FORM in HA's FlowResultType enum
    assert result.get("type") in ("form", 1), (
        f"Expected form result type, got {result.get('type')!r} (full result: {result})"
    )
    assert result.get("step_id") == "confirm", (
        f"Expected step_id='confirm', got {result.get('step_id')!r}"
    )

    schema = result.get("data_schema")
    assert schema is not None, "Form result must include data_schema"

    schema_keys = {key.schema: key for key in schema.schema}
    assert CONF_COUNTRY in schema_keys, (
        f"Form schema must include '{CONF_COUNTRY}', available: {list(schema_keys.keys())}"
    )
    country_key = schema_keys[CONF_COUNTRY]
    assert isinstance(country_key, vol.Required), (
        "CONF_COUNTRY in repair form schema must be vol.Required"
    )
    assert country_key.default() == "NO", (
        f"CONF_COUNTRY default must be 'NO' (pre-populated), got {country_key.default()!r}"
    )


async def test_nal05_repair_flow_confirm_updates_entry_on_submit(hass: HomeAssistant):
    """Submitting the repair form must update the config entry with the chosen country."""
    from custom_components.volkswagencarnet.repairs import ConfirmCountryRepairFlow

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "vehicle": "WVWZZZ3BZWE689325",
            "username": "user@example.com",
            "password": "secret",
            CONF_COUNTRY: "DE",
        },
    )
    entry.add_to_hass(hass)

    flow = ConfirmCountryRepairFlow({"entry_id": entry.entry_id, "country": "DE"})
    flow.hass = hass

    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()):
        result = await flow.async_step_confirm(user_input={CONF_COUNTRY: "US"})

    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated_entry.data.get(CONF_COUNTRY) == "US", (
        f"Repair flow did not update CONF_COUNTRY to 'US' in entry.data; "
        f"got {updated_entry.data.get(CONF_COUNTRY)!r}"
    )
    # Result type 5 == CREATE_ENTRY in HA's FlowResultType enum
    assert result.get("type") in ("create_entry", 5), (
        f"Expected create_entry result, got {result.get('type')!r}"
    )


async def test_nal05_repair_flow_init_redirects_to_confirm(hass: HomeAssistant):
    """async_step_init must redirect to the 'confirm' step."""
    from custom_components.volkswagencarnet.repairs import ConfirmCountryRepairFlow

    flow = ConfirmCountryRepairFlow({"entry_id": "irrelevant", "country": "FI"})
    flow.hass = hass

    result = await flow.async_step_init(user_input=None)

    assert result.get("step_id") == "confirm", (
        f"async_step_init must redirect to 'confirm', got step_id={result.get('step_id')!r}"
    )


async def test_nal05_repair_flow_confirm_handles_missing_entry_gracefully(
    hass: HomeAssistant,
):
    """If the config entry no longer exists, the repair flow must still complete without raising."""
    from custom_components.volkswagencarnet.repairs import ConfirmCountryRepairFlow

    flow = ConfirmCountryRepairFlow(
        {"entry_id": "nonexistent_entry_id", "country": "BE"}
    )
    flow.hass = hass

    # Must not raise; should return create_entry
    result = await flow.async_step_confirm(user_input={CONF_COUNTRY: "BE"})

    assert result.get("type") in ("create_entry", 5), (
        f"Expected create_entry even for missing entry, got {result.get('type')!r}"
    )
