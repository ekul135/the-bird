"""Data coordinator for Globird Energy."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GlobirdergyApiError, GlobirdergyAuthError, GlobirdergyClient
from .const import (
    CONF_ACCOUNT_SERVICE_ID,
    CONF_IDENTIFIER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class GlobirdEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from Globird Energy API."""

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
        client = GlobirdergyClient()
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

            return data

        except GlobirdergyAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except GlobirdergyApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data")
            raise UpdateFailed(f"Unexpected error: {err}") from err
        finally:
            await client.close()
