"""Constants for the iTAG integration."""
DOMAIN = "itag_tracker"
DEFAULT_NAME = "iTAG"
RSSI_PRESENCE_THRESHOLD = -85   # Дома при RSSI >= -85
RSSI_ABSENT_THRESHOLD = -95     # Не дома при RSSI < -95
RSSI_CONNECT_THRESHOLD = -90    # Подключаться при RSSI > -90 (почти всегда)
CONNECT_TIMEOUT = 10.0

# Service UUIDs
BATTERY_SERVICE_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
BUTTON_SERVICE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
