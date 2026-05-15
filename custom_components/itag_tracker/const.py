"""Константы для iTAG Tracker."""

DOMAIN = "itag_tracker"
MANUFACTURER = "iTAG"

# UUID сервисов и характеристик
SERVICE_BATTERY = "0000180f-0000-1000-8000-00805f9b34fb"
SERVICE_BUTTON = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARGE_LVL = "00002a19-0000-1000-8000-00805f9b34fb"
BUTTON_CHAR = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Альтернативные UUID для некоторых моделей iTAG
ALT_BUTTON_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

# Пороги для присутствия
RSSI_PRESENCE_THRESHOLD = -80
RSSI_STRONG_SIGNAL = -60
CONNECTION_TIMEOUT = 30

# Время сканирования (секунды)
SCAN_INTERVAL = 10

# Платформы
PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]
