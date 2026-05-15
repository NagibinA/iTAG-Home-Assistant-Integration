"""Константы для iTAG Tracker."""

DOMAIN = "itag_tracker"
MANUFACTURER = "iTAG"
MODEL = "BLE Tracker"

# Время обновления (секунды)
SCAN_INTERVAL = 10

# Пороги RSSI
RSSI_PRESENCE_THRESHOLD = -80      # Дома/Не дома
RSSI_CONNECT_THRESHOLD = -60       # Порог для активного подключения

# Таймауты
CONNECTION_TIMEOUT = 30            # Секунд без сигнала -> отключиться
DISCONNECT_DELAY = 60              # Секунд после потери сигнала

# UUID для iTAG (по данным из BLE Monitor)
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
BUTTON_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
BUTTON_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Альтернативные UUID (если стандартные не работают)
ALT_BUTTON_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"

# Сервисы
SERVICES = []
