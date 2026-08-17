"""Repairs flow for Volkswagen Connect integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant

from .const import CONF_COUNTRY, COUNTRY_LIST, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfirmCountryRepairFlow(RepairsFlow):
    """Repair flow: user confirms their country after v3->v4 migration."""

    def __init__(self, data: dict) -> None:
        """Initialize the repair flow."""
        super().__init__()
        self._entry_id: str = data.get("entry_id", "")
        self._existing_country: str = data.get("country", "DE")

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle init step -- redirect to confirm."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle confirm step -- show country dropdown, update config entry on submit."""
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry:
                data = dict(entry.data)
                data[CONF_COUNTRY] = user_input[CONF_COUNTRY]
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(self._entry_id)
                _LOGGER.info(
                    "Country confirmed as '%s' for config entry %s",
                    user_input[CONF_COUNTRY],
                    self._entry_id,
                )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY, default=self._existing_country): vol.In(
                        COUNTRY_LIST
                    ),
                }
            ),
            description_placeholders={"country": self._existing_country},
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict | None
) -> RepairsFlow:
    """Create repair flow for known issues."""
    if issue_id.startswith("confirm_country_"):
        return ConfirmCountryRepairFlow(data or {})
    raise ValueError(f"Unknown repair issue id: {issue_id}")
