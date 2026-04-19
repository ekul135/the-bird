"""The Bird API Client."""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)


def base64url_decode(data: str) -> bytes:
    """Decode base64url (JWK format) to bytes."""
    padding_needed = 4 - len(data) % 4
    if padding_needed != 4:
        data += "=" * padding_needed
    return base64.urlsafe_b64decode(data)


def jwk_to_public_key(jwk: dict):
    """Convert JWK to cryptography public key object."""
    n_bytes = base64url_decode(jwk["n"])
    e_bytes = base64url_decode(jwk["e"])

    n = int.from_bytes(n_bytes, "big")
    e = int.from_bytes(e_bytes, "big")

    public_numbers = RSAPublicNumbers(e, n)
    return public_numbers.public_key(default_backend())


def encrypt_password(password: str, public_key) -> str:
    """Encrypt password using RSA-OAEP with SHA-256."""
    encrypted = public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(encrypted).decode("utf-8")


class TheBirdAuthError(Exception):
    """Authentication error."""


class TheBirdApiError(Exception):
    """API error."""


class TheBirdNoDataError(Exception):
    """No data available for the requested date."""

class TheBirdClient:
    """Async client for The Bird API."""

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        """Initialize the client."""
        self._external_session = session
        self._session: aiohttp.ClientSession | None = None
        self._public_key = None
        self._headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8,en-AU;q=0.7",
            "content-type": "application/json",
            "origin": BASE_URL,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session with cookie jar."""
        if self._session is None:
            # Create our own session with cookie jar for login persistence
            # unsafe=True allows cookies from IP addresses and non-standard domains
            jar = aiohttp.CookieJar(unsafe=True)
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                cookie_jar=jar,
                timeout=timeout,
            )
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _get_public_key(self):
        """Fetch the RSA public key from the API (JWK format)."""
        session = await self._get_session()
        url = f"{BASE_URL}/api/account/publicjwk"
        async with session.get(url, headers=self._headers) as response:
            response.raise_for_status()
            jwk = await response.json()
            self._public_key = jwk_to_public_key(jwk)
            _LOGGER.debug("Fetched public key from API")
            return self._public_key

    async def login(self, email: str, password: str) -> bool:
        """Login with email and password.

        Args:
            email: Email address
            password: Plaintext password (will be encrypted)

        Returns:
            True if login successful

        Raises:
            TheBirdAuthError: If login fails
        """
        if self._public_key is None:
            await self._get_public_key()

        encrypted_password = encrypt_password(password, self._public_key)

        session = await self._get_session()
        url = f"{BASE_URL}/api/account/login"
        headers = {**self._headers, "referer": f"{BASE_URL}/login"}
        payload = {"emailAddress": email, "password": encrypted_password}

        async with session.post(url, json=payload, headers=headers) as response:
            # Must read response body for cookies to be properly captured
            response_text = await response.text()
            _LOGGER.debug("Login response status: %s", response.status)
            _LOGGER.debug("Login response cookies: %s", session.cookie_jar.filter_cookies(BASE_URL))
            
            if response.status == 200:
                _LOGGER.debug("Login successful, response: %s", response_text[:200] if response_text else "empty")
                return True
            else:
                _LOGGER.error("Login failed: %s - %s", response.status, response_text)
                raise TheBirdAuthError(f"Login failed: {response.status}")

    async def get_current_user(self) -> dict[str, Any]:
        """Get current user info including accounts after login."""
        session = await self._get_session()
        url = f"{BASE_URL}/api/account/currentuser"
        headers = {**self._headers, "referer": f"{BASE_URL}/dashboard"}

        async with session.get(url, headers=headers) as response:
            _LOGGER.debug("CurrentUser response status: %s, content-type: %s", 
                         response.status, response.content_type)
            
            if response.content_type != "application/json":
                text = await response.text()
                _LOGGER.error("CurrentUser returned non-JSON (%s): %s", 
                             response.content_type, text[:500])
                raise TheBirdAuthError("Session not authenticated - received HTML instead of JSON")
            
            response.raise_for_status()
            data = await response.json()
            
            if not data.get("success"):
                raise TheBirdApiError(f"API error: {data.get('message')}")
                
            return data.get("data", {})

    async def get_accounts(self) -> list[dict[str, Any]]:
        """Get list of accounts to find accountServiceId and identifier.
        
        Returns list of services with accountServiceId and siteIdentifier.
        """
        user_data = await self.get_current_user()
        
        accounts = user_data.get("accounts", [])
        services = []
        
        for account in accounts:
            account_number = account.get("accountNumber")
            account_address = account.get("accountAddress", "")
            
            for service in account.get("services", []):
                services.append({
                    "accountServiceId": service.get("accountServiceId"),
                    "identifier": service.get("siteIdentifier"),
                    "address": service.get("siteAddress", account_address),
                    "serviceType": service.get("serviceType"),
                    "accountNumber": account_number,
                })
        
        _LOGGER.debug("Found %d services", len(services))
        return services

    async def get_account_balance(self, account_number: str) -> dict[str, Any]:
        """Fetch account balance.

        Args:
            account_number: The account number

        Returns:
            JSON response with balance data
        """
        session = await self._get_session()
        url = f"{BASE_URL}/api/transaction/balance"
        headers = {**self._headers, "referer": f"{BASE_URL}/dashboard"}
        params = {"accountId": account_number}

        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                text = await response.text()
                _LOGGER.error("Failed to get account balance: %s - %s", response.status, text)
                raise TheBirdApiError(f"API error: {response.status}")
            data = await response.json()
            if not data.get("success"):
                raise TheBirdApiError(f"API error: {data.get('message')}")
            return data.get("data", {})

    async def get_billing_history(
        self, account_number: str, limit: int = 1
    ) -> list[dict[str, Any]]:
        """Fetch billing/invoice history.

        Args:
            account_number: The account number
            limit: Number of invoices to return

        Returns:
            List of invoice records
        """
        session = await self._get_session()
        url = f"{BASE_URL}/api/transaction/invoice"
        headers = {**self._headers, "referer": f"{BASE_URL}/billingHistory"}
        params = {"accountId": account_number}
        payload = {
            "startDate": None,
            "endDate": None,
            "offset": 0,
            "limit": limit,
        }

        async with session.post(url, json=payload, headers=headers, params=params) as response:
            if response.status != 200:
                text = await response.text()
                _LOGGER.error("Failed to get billing history: %s - %s", response.status, text)
                raise TheBirdApiError(f"API error: {response.status}")
            data = await response.json()
            if not data.get("success"):
                raise TheBirdApiError(f"API error: {data.get('message')}")
            return data.get("data", {}).get("data", [])

    async def get_unbilled_usage(
        self,
        account_service_id: int,
        identifier: str,
        account_number: str,
    ) -> dict[str, Any]:
        """Calculate unbilled usage since last invoice.

        Args:
            account_service_id: The account service ID
            identifier: The meter identifier (NMI)
            account_number: The account number

        Returns:
            Dict with unbilled_amount and billing_period_start
        """
        # Get most recent invoice to find billing period start
        invoices = await self.get_billing_history(account_number, limit=1)
        if not invoices:
            raise TheBirdApiError("No invoices found")

        last_invoice_date = invoices[0].get("issuedDate", "")[:10]  # "2026-04-06"

        # Fetch cost detail from day after last invoice to today
        from_date = (
            datetime.strptime(last_invoice_date, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")

        if from_date >= to_date:
            return {
                "unbilled_amount": 0.0,
                "billing_period_start": from_date,
            }

        response = await self.get_cost_detail(
            account_service_id=account_service_id,
            identifier=identifier,
            from_date=from_date,
            to_date=to_date,
        )

        data = response.get("data", []) if isinstance(response, dict) else response
        unbilled = 0.0

        if data and isinstance(data, list):
            for item in data:
                amount = item.get("amount", 0.0) or 0.0
                unbilled += amount

        return {
            "unbilled_amount": round(unbilled, 2),
            "billing_period_start": from_date,
        }

    async def get_cost_detail(
        self,
        account_service_id: int,
        identifier: str,
        from_date: str,
        to_date: str,
        is_smart: bool = True,
    ) -> dict[str, Any]:
        """Fetch cost detail from API.

        Args:
            account_service_id: The account service ID
            identifier: The meter identifier (NMI)
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            is_smart: Whether it's a smart meter

        Returns:
            JSON response from API
        """
        session = await self._get_session()
        url = f"{BASE_URL}/api/transaction/CostDetail"
        headers = {**self._headers, "referer": f"{BASE_URL}/usagechart"}
        payload = {
            "accountServiceId": account_service_id,
            "identifier": identifier,
            "from": from_date,
            "to": to_date,
            "isSmart": is_smart,
        }

        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                _LOGGER.error("Failed to get cost detail: %s - %s", response.status, text)
                raise TheBirdApiError(f"API error: {response.status}")
            return await response.json()

    async def get_daily_data(
        self, account_service_id: int, identifier: str, days_back: int = 1
    ) -> dict[str, Any]:
        """Get daily usage data.

        Args:
            account_service_id: The account service ID
            identifier: The meter identifier (NMI)
            days_back: Number of days to look back (default 1 for yesterday)

        Returns:
            Processed daily data with usage, costs, solar export, and credits.
            Returns None values if no data available for the requested date.
        """
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        # API uses YYYY/MM/DD format in response
        target_date_api_format = from_date.replace("-", "/")

        response = await self.get_cost_detail(
            account_service_id=account_service_id,
            identifier=identifier,
            from_date=from_date,
            to_date=to_date,
        )

        # Process the response - API returns {data: [...], success: true}
        result = {
            "date": from_date,
            # Grid usage
            "grid_usage_kwh": None,
            "grid_usage_cost": None,
            # Solar export
            "solar_export_kwh": None,
            "solar_export_credit": None,
            # Super Export top up (additional solar incentive)
            "super_export_kwh": None,
            "super_export_credit": None,
            # Supply charge
            "supply_charge": None,
            # Credits
            "zerohero_credit": None,
            # Totals
            "total_cost": None,
            "raw_data": response,
        }

        data = response.get("data", []) if isinstance(response, dict) else response

        if not data or not isinstance(data, list) or len(data) == 0:
            # No data available - raise exception so coordinator keeps previous values
            raise TheBirdNoDataError(f"No data available for date {from_date}")

        # Filter to only the target date (API may return multiple days)
        target_items = [
            item for item in data 
            if item.get("date") == target_date_api_format
        ]

        if not target_items:
            # No data for the specific date we want
            raise TheBirdNoDataError(f"No data for target date {from_date}")

        # Initialize totals now that we have data
        result["grid_usage_kwh"] = 0.0
        result["grid_usage_cost"] = 0.0
        result["solar_export_kwh"] = 0.0
        result["solar_export_credit"] = 0.0
        result["super_export_kwh"] = 0.0
        result["super_export_credit"] = 0.0
        result["supply_charge"] = 0.0
        result["zerohero_credit"] = 0.0
        result["total_cost"] = 0.0

        for item in target_items:
            category = item.get("chargeCategory", "").upper()
            amount = item.get("amount", 0.0) or 0.0
            quantity = item.get("quantity", 0.0) or 0.0

            if category == "USAGE":
                result["grid_usage_kwh"] = quantity
                result["grid_usage_cost"] = amount
            elif category == "SOLAR":
                result["solar_export_kwh"] = quantity
                result["solar_export_credit"] = abs(amount)  # Store as positive
            elif "SUPER EXPORT" in category or "EXPORT TOP" in category.upper():
                result["super_export_kwh"] = quantity
                result["super_export_credit"] = abs(amount)
            elif "ZEROHERO" in category:
                result["zerohero_credit"] = abs(amount)
            elif category == "SUPPLY":
                result["supply_charge"] = amount

            result["total_cost"] += amount

        return result
