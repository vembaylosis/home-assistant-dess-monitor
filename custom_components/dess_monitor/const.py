# This is the internal name of the integration, it should also match the directory
# name for the integration.
DOMAIN = "dess_monitor"

CONF_MAIN_UPDATE_INTERVAL = "main_update_interval"
CONF_DIRECT_UPDATE_INTERVAL = "direct_update_interval"
CONF_DYNAMIC_SETTINGS_INTERVAL = "dynamic_settings_interval"

DEFAULT_MAIN_UPDATE_INTERVAL = 60
DEFAULT_DIRECT_UPDATE_INTERVAL = 10
# Per-entity polling for dynamic select/number settings (output priority,
# max charging current, etc.) — these change rarely outside HA, so default
# refresh is 5 min to keep the cloud quiet and avoid blocking the event loop.
DEFAULT_DYNAMIC_SETTINGS_INTERVAL = 300

MIN_MAIN_UPDATE_INTERVAL = 30
MAX_MAIN_UPDATE_INTERVAL = 900
MIN_DIRECT_UPDATE_INTERVAL = 5
MAX_DIRECT_UPDATE_INTERVAL = 600
MIN_DYNAMIC_SETTINGS_INTERVAL = 60
MAX_DYNAMIC_SETTINGS_INTERVAL = 3600

# Hard ceiling on a single ctrl-value/control API call. Anything slower
# would block the entity's update slot past HA's 10s warning threshold.
DYNAMIC_SETTINGS_API_TIMEOUT = 5

# WebSocket telemetry stream — pushes per-device data to the coordinator
# without round-tripping through the polling endpoints. Off by default
# because not every devcode publishes useful frames over WS.
CONF_ENABLE_WEBSOCKET = "enable_websocket"
DEFAULT_ENABLE_WEBSOCKET = False
# Coalesce bursts of WS frames into one coordinator refresh — typical devices
# emit several frames within a few hundred ms after a state change, and
# pushing every one to all entities is wasteful.
WEBSOCKET_REFRESH_DEBOUNCE_SECONDS = 0.75
