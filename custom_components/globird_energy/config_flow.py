"""Config flow for Globird Energy integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GlobirdergyAuthError, GlobirdergyClient
from .const import CONF_ACCOUNT_SERVICE_ID, CONF_IDENTIFIER, DOMAIN

_LOGGER = logging.getLogger(__name__)


class GlobirdEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Globird Energy."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str | None = None
        self._password: str | None = None
        self._accounts: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - login credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]

            try:
                session = async_get_clientsession(self.hass)
                client = GlobirdergyClient(session)
                await client.login(self._email, self._password)
                
                # Fetch accounts to get service IDs
                self._accounts = await client.get_accounts()
                
                if self._accounts:
                    return await self.async_step_account()
                else:
                    errors["base"] = "no_accounts"

            except GlobirdergyAuthError:
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle account selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Parse selected account
            selected = user_input["account"]
            parts = selected.split("|")
            account_service_id = int(parts[0])
            identifier = parts[1]

            # Check for existing entry
            await self.async_set_unique_id(f"{self._email}_{identifier}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Globird Energy ({identifier})",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_ACCOUNT_SERVICE_ID: account_service_id,
                    CONF_IDENTIFIER: identifier,
                },
            )

        # Build account options
        account_options = {}
        for account in self._accounts:
            services = account.get("services", [])
            for service in services:
                service_id = service.get("accountServiceId")
                identifier = service.get("identifier", service.get("nmi", "Unknown"))
                address = account.get("address", {})
                address_str = address.get("fullAddress", "Unknown Address")
                
                key = f"{service_id}|{identifier}"
                account_options[key] = f"{identifier} - {address_str}"

        if not account_options:
            # Fallback to manual entry if account parsing fails
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required("account"): vol.In(account_options),
                }
            ),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual account entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            account_service_id = user_input[CONF_ACCOUNT_SERVICE_ID]
            identifier = user_input[CONF_IDENTIFIER]

            await self.async_set_unique_id(f"{self._email}_{identifier}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Globird Energy ({identifier})",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_ACCOUNT_SERVICE_ID: account_service_id,
                    CONF_IDENTIFIER: identifier,
                },
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT_SERVICE_ID): int,
                    vol.Required(CONF_IDENTIFIER): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "hint": "Enter your Account Service ID and NMI/Identifier manually."
            },
        )
