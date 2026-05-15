"""iTAG device handler - persistent connection."""
from __future__ import annotations

import asyncio
import logging
from bleak import BleakClient
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_SERVICE_UUID,
    BUTTON_SERVICE_UUID,
    CONNECT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class ITAGDevice:
    """Representation of iTAG device with persistent connection."""

    def __init__(self, hass: HomeAssistant, mac: str, name: str) -> None:
        self.hass = hass
        self.mac = mac
        self.name = name
        self._rssi = None
        self._battery = None
        self._button_pressed = False
        self._available = False
        self._client = None
        self._is_connected = False
        self._read_task = None

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
        """Update device data - called every 30 seconds for RSSI only."""
        # Получаем RSSI из рекламных данных
        service_info = bluetooth.async_last_service_info(
            self.hass, self.mac, connectable=True
        )
        
        if service_info and service_info.rssi is not None:
            self._rssi = service_info.rssi
            self._available = True
            
            # Если нет соединения и нет задачи чтения - запускаем
            if not self._is_connected and not self._read_task:
                _LOGGER.info("Starting persistent connection...")
                self._read_task = asyncio.create_task(self._persistent_connection())
        else:
            self._available = False

        return self._get_data_dict()

    async def _persistent_connection(self) -> None:
        """Maintain persistent connection and read data periodically."""
        try:
            # Подключаемся
            _LOGGER.info("Connecting to %s...", self.mac)
            self._client = BleakClient(self.mac, timeout=CONNECT_TIMEOUT)
            await self._client.connect()
            
            if not self._client.is_connected:
                _LOGGER.error("Failed to connect")
                self._is_connected = False
                self._read_task = None
                return
            
            self._is_connected = True
            _LOGGER.info("Connected! Reading button every second...")
            
            # Цикл чтения данных
            read_count = 0
            while self._is_connected:
                # Проверяем, живы ли рекламные данные
                service_info = bluetooth.async_last_service_info(
                    self.hass, self.mac, connectable=True
                )
                
                # Если пропали рекламные пакеты - отключаемся
                if not service_info or service_info.rssi is None:
                    _LOGGER.info("Device disappeared, disconnecting...")
                    break
                
                self._rssi = service_info.rssi
                
                # Читаем батарею (раз в 60 секунд, примерно каждые 60 итераций)
                read_count += 1
                if read_count >= 60:  # ~60 секунд
                    read_count = 0
                    try:
                        battery_data = await self._client.read_gatt_char(BATTERY_SERVICE_UUID)
                        if battery_data and len(battery_data) > 0:
                            if self._battery != battery_data[0]:
                                self._battery = battery_data[0]
                                _LOGGER.info("Battery: %s%%", self._battery)
                    except Exception as e:
                        _LOGGER.debug("Battery read error: %s", e)
                
                # Читаем кнопку (каждую секунду)
                try:
                    button_data = await self._client.read_gatt_char(BUTTON_SERVICE_UUID)
                    if button_data and len(button_data) > 0:
                        old_state = self._button_pressed
                        self._button_pressed = button_data[0] == 1
                        if old_state != self._button_pressed:
                            _LOGGER.info("🔘 Button: %s", "PRESSED" if self._button_pressed else "normal")
                except Exception as e:
                    _LOGGER.debug("Button read error: %s", e)
                
                await asyncio.sleep(1)  # Пауза 1 секунда между чтениями
                
        except asyncio.CancelledError:
            _LOGGER.debug("Connection task cancelled")
        except Exception as e:
            _LOGGER.error("Connection error: %s", e)
        finally:
            # Отключаемся
            if self._client and self._client.is_connected:
                try:
                    await self._client.disconnect()
                    _LOGGER.info("Disconnected from %s", self.mac)
                except:
                    pass
            self._is_connected = False
            self._client = None
            self._read_task = None

    async def stop(self) -> None:
        """Stop persistent connection."""
        _LOGGER.info("Stopping persistent connection...")
        self._is_connected = False
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except:
                pass
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except:
                pass
        self._client = None
        self._read_task = None

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
