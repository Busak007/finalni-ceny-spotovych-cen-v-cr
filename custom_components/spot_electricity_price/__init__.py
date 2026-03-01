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
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload_platforms(entry, ["sensor"])
