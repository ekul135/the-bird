"""Globird Energy API Client."""
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


class GlobirdergyAuthError(Exception):
    """Authentication error."""


class GlobirdergyApiError(Exception):
    """API error."""


class GlobirdergyClient:
    """Async client for Globird Energy API."""

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
            GlobirdergyAuthError: If login fails
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
                raise GlobirdergyAuthError(f"Login failed: {response.status}")

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
                raise GlobirdergyAuthError("Session not authenticated - received HTML instead of JSON")
            
            response.raise_for_status()
            data = await response.json()
            
            if not data.get("success"):
                raise GlobirdergyApiError(f"API error: {data.get('message')}")
                
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
                raise GlobirdergyApiError(f"API error: {response.status}")
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
            Processed daily data with usage, cost, supply charge, and total
        """
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        data = await self.get_cost_detail(
            account_service_id=account_service_id,
            identifier=identifier,
            from_date=from_date,
            to_date=to_date,
        )

        # Process the response to extract daily totals
        result = {
            "date": from_date,
            "usage_kwh": 0.0,
            "usage_cost": 0.0,
            "supply_charge": 0.0,
            "total_cost": 0.0,
            "raw_data": data,
        }

        if data and isinstance(data, list) and len(data) > 0:
            day_data = data[0] if isinstance(data, list) else data
            
            # Sum up interval usage if available
            if "intervals" in day_data:
                for interval in day_data["intervals"]:
                    result["usage_kwh"] += interval.get("usage", 0)
                    result["usage_cost"] += interval.get("cost", 0)
            
            # Get daily totals if available
            result["usage_kwh"] = day_data.get("totalUsage", result["usage_kwh"])
            result["usage_cost"] = day_data.get("totalCost", result["usage_cost"])
            result["supply_charge"] = day_data.get("supplyCharge", 0)
            result["total_cost"] = result["usage_cost"] + result["supply_charge"]

        return result
