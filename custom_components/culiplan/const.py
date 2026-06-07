"""Constants for the Culiplan integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "culiplan"

# OAuth client ID for the Home Assistant Core integration. The Culiplan
# backend treats this as a public PKCE client (no client_secret).
OAUTH_CLIENT_ID = "ha-core"
BASE_URL = "https://api.culiplan.com"

OAUTH2_AUTHORIZE = f"{BASE_URL}/api/oauth/authorize"
OAUTH2_TOKEN = f"{BASE_URL}/api/oauth/token"

# OAuth scopes requested for the ha-core client. Must be a subset of the
# allowed scopes registered for "ha-core" in the backend.
OAUTH2_SCOPES: tuple[str, ...] = (
    "calendar:read",
    "todo:read",
    "todo:write",
    "pantry:read",
    "meals:read",
    "shopping:read",
    "shopping:write",
    "recipes:read",
    "profile:read",
    "household:read",
    "openid",
    "offline_access",
)

# Options keys
CONF_EXPIRY_DAYS = "expiry_days"
CONF_EXPIRY_HOURS = "expiry_hours"

DEFAULT_EXPIRY_DAYS = 3
DEFAULT_EXPIRY_HOURS = 48

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.TODO,
]
