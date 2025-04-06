"""Spot Electricity Price integration."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry

DOMAIN = "spot_electricity_price"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Spot Electricity Price component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spot Electricity Price from a config entry."""
    # Forward the entry setup to both sensor and binary_sensor platforms
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "binary_sensor")
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload both sensor and binary_sensor platforms
    unload_sensor = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    unload_binary_sensor = await hass.config_entries.async_forward_entry_unload(entry, "binary_sensor")
    return unload_sensor and unload_binary_sensor
