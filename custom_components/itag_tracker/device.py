"""iTAG device handler - persistent connection with smart battery reading."""
from __future__ import annotations

import asyncio
import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_SERVICE_UUID,
    CONNECT_TIMEOUT,
    RSSI_OFFLINE_VALUE,
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
        self._available = False
        self._client = None
        self._is_connected = False
        self._read_task = None
        self._device = None
        self._battery_100_count = 0

    @property
    def rssi(self) -> int | None:
        return self._rssi

    @property
    def battery(self) -> int | None:
        return self._battery

    @property
    def available(self) -> bool:
        return self._available

    async def update(self) -> dict:
        """Update RSSI - called every 30 seconds."""
        service_info = bluetooth.async_last_service_info(
            self.hass, self.mac, connectable=True
        )
        
        if service_info and service_info.rssi is not None:
            self._rssi = service_info.rssi
            self._available = True
            self._device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            
            if self._device and not self._is_connected and (self._read_task is None or self._read_task.done()):
                _LOGGER.info("Starting persistent connection...")
                self._read_task = asyncio.create_task(self._persistent_connection())
        else:
            self._rssi = RSSI_OFFLINE_VALUE
            self._available = False

        return self._get_data_dict()

    async def _read_battery_until_real(self) -> int | None:
        """Read battery, discarding placeholder 100% values."""
        try:
            for attempt in range(6):  # максимум 6 попыток (~6-8 секунд)
                battery_data = await self._client.read_gatt_char(BATTERY_SERVICE_UUID)
                if battery_data and len(battery_data) > 0:
                    value = battery_data[0]
                    if value < 100:
                        if attempt > 0:
                            _LOGGER.debug("Real battery value: %s%% (after %s attempts)", value, attempt + 1)
                        return value
                    else:
                        _LOGGER.debug("Got placeholder 100%%, attempt %s/6, waiting...", attempt + 1)
                await asyncio.sleep(1.5)  # Пауза между попытками
            
            _LOGGER.warning("Failed to get real battery value after 6 attempts")
            return None
            
        except Exception as e:
            _LOGGER.debug("Battery read error: %s", e)
            return None

    async def _persistent_connection(self) -> None:
        """Maintain connection and poll battery."""
        try:
            _LOGGER.info("Connecting to %s...", self.mac)
            self._client = await establish_connection(
                BleakClient,
                self._device,
                self.name,
                max_attempts=3,
                timeout=CONNECT_TIMEOUT,
            )
            
            if not self._client.is_connected:
                _LOGGER.error("Failed to connect")
                self._is_connected = False
                return
            
            self._is_connected = True
            _LOGGER.info("Connected! Starting smart battery polling...")
            
            # Сразу читаем батарею после подключения
            real_battery = await self._read_battery_until_real()
            if real_battery is not None:
                self._battery = real_battery
                _LOGGER.info("Initial battery: %s%%", self._battery)
            
            # Цикл чтения батареи
            while self._is_connected:
                # Проверяем, живо ли устройство
                service_info = bluetooth.async_last_service_info(
                    self.hass, self.mac, connectable=True
                )
                if not service_info or service_info.rssi is None:
                    _LOGGER.info("Device disappeared, closing connection...")
                    break
                
                # Читаем батарею умным методом
                real_battery = await self._read_battery_until_real()
                
                if real_battery is not None:
                    # Защита от залипания
                    if real_battery == 100:
                        self._battery_100_count += 1
                        if self._battery_100_count >= 4:
                            _LOGGER.warning("Battery stuck at 100%%, forcing reconnection...")
                            break
                    else:
                        self._battery_100_count = 0
                    
                    if self._battery != real_battery:
                        self._battery = real_battery
                        _LOGGER.info("Battery: %s%%", self._battery)
                else:
                    _LOGGER.debug("Failed to read battery")
                
                # Пауза между циклами (30 секунд)
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            _LOGGER.debug("Connection task cancelled")
        except Exception as e:
            _LOGGER.error("Connection error: %s", e)
        finally:
            if self._client and self._client.is_connected:
                try:
                    await self._client.disconnect()
                    _LOGGER.info("Disconnected")
                except:
                    pass
            self._is_connected = False
            self._client = None
            self._read_task = None

    async def stop(self) -> None:
        """Stop persistent connection."""
        self._is_connected = False
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except:
                pass

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "available": self._available,
        }
