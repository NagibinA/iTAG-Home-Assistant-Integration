"""Icon definitions for iTAG integration."""

def get_icon(icon_name: str, state=None) -> str:
    """Return icon for given name and state."""
    if icon_name == "battery_sensor" and state is not None:
        if isinstance(state, (int, float)):
            if state >= 95:
                return "mdi:battery"
            elif state >= 70:
                return "mdi:battery-90"
            elif state >= 50:
                return "mdi:battery-80"
            elif state >= 30:
                return "mdi:battery-60"
            elif state >= 20:
                return "mdi:battery-50"
            elif state >= 10:
                return "mdi:battery-30"
            elif state > 5:
                return "mdi:battery-20"
            else:
                return "mdi:battery-10"
        return "mdi:battery"
    
    if icon_name == "rssi_sensor" and state is not None:
        if isinstance(state, (int, float)):
            if state > -50:
                return "mdi:signal-4"
            elif state > -65:
                return "mdi:signal-3"
            elif state > -80:
                return "mdi:signal-2"
            else:
                return "mdi:signal-1"
        return "mdi:signal"
    
    if icon_name == "button_sensor":
        return "mdi:gesture-tap-button"
    
    return "mdi:bluetooth"
