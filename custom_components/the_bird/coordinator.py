"""Data coordinator for The Bird."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TheBirdApiError, TheBirdAuthError, TheBirdClient, TheBirdNoDataError
from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_ACCOUNT_SERVICE_ID,
    CONF_IDENTIFIER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class TheBirdCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from The Bird API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        client = TheBirdClient()
        try:
            # Login
            await client.login(
                self.entry.data[CONF_EMAIL],
                self.entry.data[CONF_PASSWORD],
            )

            # Fetch daily data
            data = await client.get_daily_data(
                account_service_id=self.entry.data[CONF_ACCOUNT_SERVICE_ID],
                identifier=self.entry.data[CONF_IDENTIFIER],
                days_back=1,
            )

            # Only update if data date has changed
            if self.data is not None:
                if data.get("date") == self.data.get("date"):
                    return self.data

            # Fetch account balance
            account_number = self.entry.data.get(CONF_ACCOUNT_NUMBER)
            if account_number:
                try:
                    balance_data = await client.get_account_balance(account_number)
                    data["account_balance"] = -(balance_data.get("balance") or 0)
                except Exception as err:
                    _LOGGER.warning("Failed to fetch account balance: %s", err)
                    data["account_balance"] = None

                # Fetch unbilled usage since last invoice
                try:
                    unbilled_data = await client.get_unbilled_usage(
                        account_service_id=self.entry.data[CONF_ACCOUNT_SERVICE_ID],
                        identifier=self.entry.data[CONF_IDENTIFIER],
                        account_number=account_number,
                    )
                    data["unbilled_amount"] = unbilled_data.get("unbilled_amount")
                    balance = data.get("account_balance")
                    unbilled = data.get("unbilled_amount")
                    if balance is not None and unbilled is not None:
                        data["estimated_balance"] = round(balance + unbilled, 2)
                    else:
                        data["estimated_balance"] = None
                except Exception as err:
                    _LOGGER.warning("Failed to fetch unbilled usage: %s", err)
                    data["unbilled_amount"] = None
                    data["estimated_balance"] = None

            return data

        except TheBirdNoDataError as err:
            # No data available yet - keep previous values
            _LOGGER.debug("No data available: %s", err)
            if self.data is not None:
                return self.data  # Keep previous values
            raise UpdateFailed(f"No data available: {err}") from err
        except TheBirdAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except TheBirdApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data")
            raise UpdateFailed(f"Unexpected error: {err}") from err
        finally:
            await client.close()
