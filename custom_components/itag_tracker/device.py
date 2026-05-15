"""iTAG device handler using Home Assistant Bluetooth components."""
from __future__ import annotations

import asyncio
import logging
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    async_last_service_info,
    BluetoothServiceInfoBleak,
)

from .const import (
    BATTERY_SERVICE_UUID,
    BUTTON_SERVICE_UUID,
    CONNECT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class ITAGDevice:
    """Representation of iTAG device using HA Bluetooth."""

    def __init__(self, hass: HomeAssistant, mac: str, name: str) -> None:
        """Initialize the device."""
        self.hass = hass
        self.mac = mac
        self.name = name
        self._rssi = None
        self._battery = None
        self._button_pressed = False
        self._available = False
        self._client = None
        self._keep_connected = False
        self._connect_task = None
        self._device = None

    @property
    def rssi(self) -> int | None:
        return self._rssi

    @property
    def battery(self) -> int | None:
        return self._battery

    @property
    def button_pressed(self) -> bool:
        return self._button_pressed

    @property
    def available(self) -> bool:
        return self._available

    async def update(self) -> dict:
        """Update device data - called every 30 seconds."""
        # Получаем RSSI из рекламных данных
        service_info = async_last_service_info(
            self.hass, self.mac, connectable=True
        )
        
        if service_info and service_info.rssi is not None:
            self._rssi = service_info.rssi
            _LOGGER.info("RSSI: %s", self._rssi)
            self._available = True
            self._device = async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            
            # Если нет соединения - запускаем постоянное подключение
            if not self._keep_connected and self._device:
                _LOGGER.info("Starting persistent connection...")
                self._keep_connected = True
                if self._connect_task is None or self._connect_task.done():
                    self._connect_task = asyncio.create_task(self._persistent_connection())
        else:
            self._available = False

        return self._get_data_dict()

    async def _persistent_connection(self) -> None:
        """Keep connection alive and listen for notifications."""
        from bleak_retry_connector import establish_connection, BleakClientWithServiceCache
        
        while self._keep_connected:
            try:
                # Проверяем, живы ли рекламные данные
                service_info = async_last_service_info(
                    self.hass, self.mac, connectable=True
                )
                
                if not service_info or service_info.rssi is None:
                    _LOGGER.debug("No advertising data, waiting...")
                    await asyncio.sleep(5)
                    continue
                
                if not self._device:
                    self._device = async_ble_device_from_address(
                        self.hass, self.mac, connectable=True
                    )
                    if not self._device:
                        await asyncio.sleep(5)
                        continue
                
                if self._client and self._client.is_connected:
                    # Уже подключены, просто читаем батарею раз в 60 секунд
                    await asyncio.sleep(60)
                    await self._read_battery()
                    continue
                
                # Подключаемся через bleak-retry-connector
                _LOGGER.info("Connecting to %s...", self.mac)
                self._client = await establish_connection(
                    BleakClientWithServiceCache,
                    self._device,
                    self.name,
                    max_attempts=3,
                    timeout=CONNECT_TIMEOUT,
                )
                
                if not self._client.is_connected:
                    _LOGGER.warning("Failed to connect")
                    await asyncio.sleep(10)
                    continue
                
                _LOGGER.info("Connected!")
                
                # Включаем уведомления для кнопки
                try:
                    await self._client.start_notify(BUTTON_SERVICE_UUID, self._button_callback)
                    _LOGGER.info("✅ Button notifications ENABLED! Press the button.")
                except Exception as e:
                    _LOGGER.error("Failed to enable notifications: %s", e)
                    # Пробуем через характеристику
                    try:
                        char = self._client.services.get_characteristic(BUTTON_SERVICE_UUID)
                        if char:
                            await self._client.start_notify(char, self._button_callback)
                            _LOGGER.info("✅ Button notifications ENABLED via char!")
                    except Exception as e2:
                        _LOGGER.error("Alternative also failed: %s", e2)
                
                # Читаем батарею при подключении
                await self._read_battery()
                
                # Держим соединение открытым
                while self._keep_connected:
                    # Проверяем, живы ли рекламные данные
                    service_info = async_last_service_info(
                        self.hass, self.mac, connectable=True
                    )
                    if not service_info or service_info.rssi is None:
                        _LOGGER.debug("Device disappeared, will reconnect later")
                        break
                    
                    # Раз в 60 секунд читаем батарею
                    await asyncio.sleep(60)
                    await self._read_battery()
                
            except asyncio.CancelledError:
                _LOGGER.debug("Connection task cancelled")
                break
            except Exception as e:
                _LOGGER.error("Connection error: %s", e)
                await asyncio.sleep(10)
            finally:
                if self._client and self._client.is_connected:
                    try:
                        await self._client.disconnect()
                        _LOGGER.info("Disconnected")
                    except:
                        pass
                self._client = None
        
        _LOGGER.info("Persistent connection stopped")

    def _button_callback(self, sender, data):
        """Called when button is pressed."""
        _LOGGER.warning("🔔🔔🔔 BUTTON NOTIFICATION RECEIVED! 🔔🔔🔔")
        _LOGGER.warning("Raw data: %s", data.hex() if data else None)
        if data and len(data) > 0:
            old_state = self._button_pressed
            self._button_pressed = data[0] == 1
            _LOGGER.warning("Button state: %s -> %s", 
                           "PRESSED" if old_state else "normal",
                           "PRESSED" if self._button_pressed else "normal")

    async def _read_battery(self) -> None:
        """Read battery level."""
        if not self._client or not self._client.is_connected:
            return
        
        try:
            battery_data = await self._client.read_gatt_char(BATTERY_SERVICE_UUID)
            if battery_data and len(battery_data) > 0:
                self._battery = battery_data[0]
                _LOGGER.debug("Battery: %s%%", self._battery)
        except Exception as e:
            _LOGGER.warning("Battery read error: %s", e)

    async def stop(self) -> None:
        """Stop persistent connection."""
        self._keep_connected = False
        if self._connect_task and not self._connect_task.done():
            self._connect_task.cancel()
        if self._client and self._client.is_connected:
            await self._client.disconnect()

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
