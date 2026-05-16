"""Simple icon definitions for iTAG integration."""

def get_icon(icon_name: str, state=None) -> str:
    """Return icon for given name."""
    if icon_name == "battery_sensor":
        return "mdi:battery"

    if icon_name == "rssi_sensor":
        return "mdi:signal"

    return "mdi:bluetooth"
