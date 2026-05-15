# iTAG Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/NagibinA/iTAG-Home-Assistant-Integration)](https://github.com/NagibinA/iTAG-Home-Assistant-Integration/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Беспроводная интеграция для отслеживания BLE-брелоков iTAG в Home Assistant.

## Возможности

- 🔋 **Отслеживание заряда батареи** - показывает уровень заряда в процентах
- 🔘 **Детекция нажатия кнопки** - используйте iTAG как пульт для автоматизаций
- 📡 **Мониторинг RSSI** - уровень сигнала для оценки расстояния
- 📍 **Трекинг присутствия** - автоматически определяет, когда брелок рядом

## Поддерживаемые устройства

- Любые BLE-брелоки iTAG (AliExpress, Amazon, местные магазины)
- Клоны AirTag с поддержкой BLE
- Устройства с сервисами: 180f (Battery), 1802 (Alert), ffe0 (Button)

## Установка

### Через HACS (Рекомендуется)

1. Добавьте этот репозиторий в HACS как Custom Repository
2. Установите "iTAG Tracker"
3. Перезапустите Home Assistant

### Ручная установка

1. Скачайте последний релиз
2. Распакуйте `custom_components/itag_tracker` в папку `custom_components` вашего Home Assistant
3. Перезапустите Home Assistant

