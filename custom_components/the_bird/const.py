"""Constants for The Bird integration."""
from datetime import timedelta

DOMAIN = "the_bird"

# Configuration keys
CONF_ACCOUNT_SERVICE_ID = "account_service_id"
CONF_IDENTIFIER = "identifier"
CONF_ACCOUNT_NUMBER = "account_number"

# API
BASE_URL = "https://myaccount.globirdenergy.com.au"

# Update interval
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
