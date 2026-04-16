"""Constants for The Bird integration."""
from datetime import timedelta

DOMAIN = "the_bird"

# Configuration keys
CONF_ACCOUNT_SERVICE_ID = "account_service_id"
CONF_IDENTIFIER = "identifier"

# API
BASE_URL = "https://myaccount.globirdenergy.com.au"

# Update interval
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)

# Sensor types
SENSOR_DAILY_USAGE = "daily_usage"
SENSOR_DAILY_COST = "daily_cost"
SENSOR_DAILY_SUPPLY_CHARGE = "daily_supply_charge"
SENSOR_DAILY_TOTAL_COST = "daily_total_cost"
