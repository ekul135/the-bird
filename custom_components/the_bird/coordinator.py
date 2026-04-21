"""Data coordinator for The Bird."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TheBirdApiError, TheBirdAuthError, TheBirdClient, TheBirdNoDataError
from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_ACCOUNT_SERVICE_ID,
    CONF_IDENTIFIER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HISTORICAL_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class TheBirdCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from The Bird API."""

    # Mapping of data keys to sensor types and their metadata
    STATISTIC_SENSORS = {
        "grid_usage_kwh": {
            "key": "usage",
            "unit": UnitOfEnergy.KILO_WATT_HOUR,
            "name": "Usage",
        },
        # "grid_usage_cost": {
        #     "key": "usage_cost",
        #     "unit": "AUD",
        #     "name": "Usage Cost",
        # },
        # "solar_export_kwh": {
        #     "key": "solar",
        #     "unit": UnitOfEnergy.KILO_WATT_HOUR,
        #     "name": "Solar Export",
        # },
        # "solar_export_credit": {
        #     "key": "solar_credit",
        #     "unit": "AUD",
        #     "name": "Solar Credit",
        # },
        # "super_export_kwh": {
        #     "key": "super_export",
        #     "unit": UnitOfEnergy.KILO_WATT_HOUR,
        #     "name": "Super Export",
        # },
        # "super_export_credit": {
        #     "key": "super_export_credit",
        #     "unit": "AUD",
        #     "name": "Super Export Credit",
        # },
        # "supply_charge": {
        #     "key": "supply",
        #     "unit": "AUD",
        #     "name": "Supply Charge",
        # },
        # "zerohero_credit": {
        #     "key": "zerohero",
        #     "unit": "AUD",
        #     "name": "ZeroHero Credit",
        # },
        # "total_cost": {
        #     "key": "net_cost",
        #     "unit": "AUD",
        #     "name": "Net Cost",
        # },
    }

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self._imported_dates: set[str] = set()
        self._historical_imported: bool = False

    async def _import_statistics(self, data: dict[str, Any]) -> None:
        """Import statistics with the correct historical date.

        This ensures energy data is attributed to the date it was actually
        recorded, not the date it was fetched.
        """
        date_str = data.get("date")
        if not date_str:
            _LOGGER.warning("No date in data, skipping statistics import")
            return

        # Check if we've already imported this date
        if date_str in self._imported_dates:
            _LOGGER.debug("Statistics for %s already imported", date_str)
            return

        # Parse the date and create a timestamp at start of day in UTC
        # Statistics should use the start of the period they represent
        try:
            data_date = datetime.fromisoformat(date_str)
            # Set to start of day in local timezone, then convert to UTC
            local_start_of_day = data_date.replace(hour=0, minute=0, second=0, microsecond=0)
            # Get local timezone
            local_tz = datetime.now().astimezone().tzinfo
            local_dt = local_start_of_day.replace(tzinfo=local_tz)
            utc_dt = local_dt.astimezone(timezone.utc)
        except ValueError as err:
            _LOGGER.error("Invalid date format %s: %s", date_str, err)
            return

        _LOGGER.info(
            "Importing statistics for %s (timestamp: %s)", date_str, utc_dt.isoformat()
        )

        identifier = self.entry.data[CONF_IDENTIFIER].lower()

        # Import statistics for each sensor
        for data_key, sensor_info in self.STATISTIC_SENSORS.items():
            value = data.get(data_key)
            if value is None:
                continue

            # Create external statistic ID in the format domain:unique_id
            # Must be lowercase, only a-z, 0-9, and underscore
            statistic_id = f"{DOMAIN}:{sensor_info['key']}"

            _LOGGER.debug("Creating statistic with ID: %s, source: %s", statistic_id, DOMAIN)

            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"The Bird {sensor_info['name']}",
                source=DOMAIN,
                statistic_id=statistic_id,
                unit_of_measurement=sensor_info["unit"],
            )

            # Create the statistic data point
            # state = daily value, sum = cumulative (we use daily value, HA accumulates)
            statistics = [
                StatisticData(
                    start=utc_dt,
                    state=value,
                    sum=value,
                )
            ]

            try:
                async_import_statistics(self.hass, metadata, statistics)
                _LOGGER.info(
                    "Imported statistic %s = %s for %s",
                    statistic_id,
                    value,
                    date_str,
                )
            except Exception as err:
                _LOGGER.exception(
                    "Failed to import statistic %s: %s", statistic_id, err
                )

        # Mark this date as imported
        self._imported_dates.add(date_str)

    async def _import_historical_data(self, client: TheBirdClient) -> None:
        """Import historical data on first run.

        Fetches the past HISTORICAL_DAYS days of data and imports statistics
        for each day, ensuring users have historical data immediately.
        """
        if self._historical_imported:
            return

        _LOGGER.info("Fetching %d days of historical data...", HISTORICAL_DAYS)

        try:
            historical_data = await client.get_historical_data(
                account_service_id=self.entry.data[CONF_ACCOUNT_SERVICE_ID],
                identifier=self.entry.data[CONF_IDENTIFIER],
                days=HISTORICAL_DAYS,
            )

            if not historical_data:
                _LOGGER.warning("No historical data available")
                self._historical_imported = True
                return

            _LOGGER.info("Importing statistics for %d days", len(historical_data))

            for daily_data in historical_data:
                await self._import_statistics(daily_data)

            self._historical_imported = True
            _LOGGER.info("Historical data import complete")

        except Exception as err:
            _LOGGER.error("Failed to import historical data: %s", err)
            # Still mark as imported to avoid retrying every update
            self._historical_imported = True

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        client = TheBirdClient()
        try:
            # Login
            await client.login(
                self.entry.data[CONF_EMAIL],
                self.entry.data[CONF_PASSWORD],
            )

            # On first run, import historical data
            if not self._historical_imported:
                await self._import_historical_data(client)

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

            # Import statistics with the correct historical date
            # This ensures energy data is attributed to the date it occurred
            await self._import_statistics(data)

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
