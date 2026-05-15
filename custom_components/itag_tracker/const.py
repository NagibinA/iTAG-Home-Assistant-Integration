"""Константы для iTAG Tracker."""

DOMAIN = "itag_tracker"
MANUFACTURER = "iTAG"

# UUID сервисов и характеристик
SERVICE_BATTERY = "0000180f-0000-1000-8000-00805f9b34fb"
SERVICE_BUTTON = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARGE_LVL = "00002a19-0000-1000-8000-00805f9b34fb"
BUTTON_CHAR = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Константы для расчёта расстояния по RSSI
DEFAULT_TX_POWER = -59  # dBm на расстоянии 1 метр
ENVIRONMENT_FACTOR = 2.5  # коэффициент среды (квартира)

# Пороги для присутствия
RSSI_PRESENCE_THRESHOLD = -80  # Если RSSI выше -80 -> брелок рядом
CONNECTION_TIMEOUT = 30  # Секунд без сигнала -> отключаемся

# Уровни расстояния (в метрах)
DISTANCE_CLOSE = 1.0    # близко: < 1 м
DISTANCE_MEDIUM = 3.0   # средне: 1-3 м
DISTANCE_FAR = 10.0     # далеко: 3-10 м, > 10 м - очень далеко