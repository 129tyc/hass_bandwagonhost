"""Constants for the KiwiVM Traffic integration."""

DOMAIN = "kiwivm_traffic"
PLATFORMS = ["sensor"]

CONF_VEID = "veid"
CONF_API_KEY = "api_key"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 15
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 60

API_URL = "https://api.64clouds.com/v1/getServiceInfo"
