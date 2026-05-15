"""Device tracker для iTAG: управление подключением, присутствие, RSSI."""

import logging
import asyncio
from datetime import datetime

from homeassistant.components.device_tracker import SourceType, ScannerEntity
from bleak import BleakScanner, BleakClient

from .const import (
    DOMAIN,
    RSSI_PRESENCE_THRESHOLD,
    CONNECTION_TIMEOUT,
    CHARGE_LVL,
    BUTTON_CHAR,
)

_LOGGER = logging.getLogger(__name__)


class iTAGDeviceTracker(ScannerEntity):
    """Отслеживание iTAG с активным подключением."""

    def __init__(self, hass, entry):
        self.hass = hass
        self._entry = entry
        self._mac = entry.data["mac_address"].lower()
        self._name = entry.data["name"]
        self._attr_name = self._name
        self._attr_unique_id = f"{self._mac}_tracker"
        
        # Состояния
        self._is_present = False
        self._rssi = None
        self._last_seen = None
        self._battery = None
        
        # Управление
        self._client = None
        self._scan_task = None
        self._running = False
        self._last_rssi_update = None
        
        # Для callback от кнопки
        self._button_callback = None

    @property
    def is_connected(self):
        return self._is_present

    @property
    def source_type(self):
        return SourceType.BLUETOOTH

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._rssi is not None:
            attrs["rssi"] = self._rssi
        if self._last_seen:
            attrs["last_seen"] = self._last_seen
        if self._battery is not None:
            attrs["battery"] = self._battery
        return attrs

    def set_button_callback(self, callback):
        """Установить callback для уведомления о нажатии кнопки."""
        self._button_callback = callback

    def get_battery(self):
        """Получить текущий заряд батареи."""
        return self._battery

    def get_rssi(self):
        """Получить текущий RSSI."""
        return self._rssi

    async def start(self):
        """Запуск сканирования."""
        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())

    async def stop(self):
        """Остановка."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
        await self._disconnect()

    async def _scan_loop(self):
        """Цикл пассивного сканирования."""
        while self._running:
            try:
                # Ищем устройство в эфире
                device = await BleakScanner.find_device_by_address(self._mac, timeout=5)
                
                if device:
                    self._rssi = device.rssi
                    self._last_seen = datetime.now().isoformat()
                    self._last_rssi_update = datetime.now()
                    
                    # Проверяем, нужно ли подключиться
                    if not self._client and device.rssi > RSSI_PRESENCE_THRESHOLD:
                        # Сигнал сильный — подключаемся
                        await self._connect()
                    
                    # Обновляем состояние присутствия
                    self._is_present = device.rssi > RSSI_PRESENCE_THRESHOLD
                    
                    _LOGGER.debug(
                        f"{self._name} RSSI: {device.rssi} dBm, present: {self._is_present}"
                    )
                else:
                    # Устройство не найдено
                    self._rssi = None
                    self._is_present = False
                    
                    # Если было подключение — отключаемся
                    if self._client:
                        await self._disconnect()
                
                # Если подключены, но давно не было обновлений — отключаемся
                if self._client and self._last_rssi_update:
                    delta = (datetime.now() - self._last_rssi_update).total_seconds()
                    if delta > CONNECTION_TIMEOUT:
                        _LOGGER.debug(f"{self._name} timeout, disconnecting")
                        await self._disconnect()
                
                self.async_write_ha_state()
                
            except Exception as e:
                _LOGGER.debug(f"Scan loop error: {e}")
            
            await asyncio.sleep(5)  # Сканируем каждые 5 секунд

    async def _connect(self):
        """Активное подключение к брелоку."""
        try:
            _LOGGER.info(f"Connecting to {self._name} ({self._mac})...")
            
            self._client = BleakClient(self._mac, timeout=10.0)
            await self._client.connect()
            
            # Читаем батарею
            battery_char = await self._client.read_gatt_char(CHARGE_LVL)
            self._battery = int(battery_char[0])
            _LOGGER.info(f"{self._name} battery: {self._battery}%")
            
            # Подписываемся на кнопку
            await self._client.start_notify(BUTTON_CHAR, self._button_notify_handler)
            _LOGGER.info(f"{self._name} button notifications enabled")
            
            _LOGGER.info(f"{self._name} connected successfully")
            
        except Exception as e:
            _LOGGER.error(f"Connection failed for {self._name}: {e}")
            await self._disconnect()

    async def _disconnect(self):
        """Отключение от брелока."""
        if self._client:
            try:
                await self._client.stop_notify(BUTTON_CHAR)
            except:
                pass
            try:
                await self._client.disconnect()
            except:
                pass
            self._client = None
            self._battery = None
            _LOGGER.debug(f"{self._name} disconnected")

    def _button_notify_handler(self, sender, data):
        """Обработчик нажатия кнопки."""
        if len(data) > 0 and data[0] == 0x01:
            _LOGGER.info(f"{self._name} button pressed")
            
            # Уведомляем binary_sensor через callback
            if self._button_callback:
                self.hass.async_create_task(self._button_callback())
