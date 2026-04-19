"""Config flow for The Bird integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .api import TheBirdAuthError, TheBirdApiError, TheBirdClient
from .const import CONF_ACCOUNT_NUMBER, CONF_ACCOUNT_SERVICE_ID, CONF_IDENTIFIER, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TheBirdConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for The Bird."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str | None = None
        self._password: str | None = None
        self._services: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - login credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]

            try:
                client = TheBirdClient()
                _LOGGER.debug("Attempting login for %s", self._email)
                await client.login(self._email, self._password)
                _LOGGER.debug("Login successful, fetching accounts")
                
                # Fetch accounts using currentuser endpoint
                self._services = await client.get_accounts()
                _LOGGER.debug("Got %d services", len(self._services))
                await client.close()
                
                if self._services:
                    return await self.async_step_account()
                else:
                    errors["base"] = "no_accounts"

            except TheBirdAuthError as err:
                _LOGGER.error("Authentication error: %s", err)
                errors["base"] = "invalid_auth"
            except TheBirdApiError as err:
                _LOGGER.error("API error: %s", err)
                errors["base"] = "cannot_connect"
            except aiohttp.ClientError as err:
                _LOGGER.error("Connection error (%s): %s", type(err).__name__, err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception (%s): %s", type(err).__name__, err)
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
            account_number = parts[2] if len(parts) > 2 else None

            # Check for existing entry
            await self.async_set_unique_id(f"{self._email}_{identifier}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"The Bird ({identifier})",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_ACCOUNT_SERVICE_ID: account_service_id,
                    CONF_IDENTIFIER: identifier,
                    CONF_ACCOUNT_NUMBER: account_number,
                },
            )

        # Build account options from services
        account_options = {}
        for service in self._services:
            service_id = service.get("accountServiceId")
            identifier = service.get("identifier", "Unknown")
            address = service.get("address", "Unknown Address")
            account_number = service.get("accountNumber", "")
            
            key = f"{service_id}|{identifier}|{account_number}"
            account_options[key] = f"{identifier} - {address}"

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required("account"): vol.In(account_options),
                }
            ),
            errors=errors,
        )
