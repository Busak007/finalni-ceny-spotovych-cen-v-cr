"""Config flow for Spot Electricity Price integration."""
import voluptuous as vol
import logging

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

DOMAIN = "spot_electricity_price"
_LOGGER = logging.getLogger(__name__)

# Konstanty pro konfiguraci
CONF_SPOT_PRICE_ENTITY = "spot_price_entity"
CONF_HDO_ENTITY = "hdo_entity"
CONF_PRODEJ = "prodej"
CONF_DAN_Z_ELEKTRINY = "dan_z_elektriny"
CONF_CENA_SYSTEMOVYCH_SLUZEB = "cena_systemovych_sluzeb"
CONF_OZE = "oze"
CONF_VYKUP = "vykup"

CONF_PRICE_NT = "price_nt"
CONF_PRICE_VT = "price_vt"
CONF_DISTRIBUTOR = "distributor"
CONF_A = "code_a"
CONF_NAME = "HDO_smart"
CONF_PSC = "smart"

REGION = ["EG.D", "ČEZ", "PRE"]

class SpotElectricityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spot Electricity Price."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validace a uložení konfigurace
                unique_id = f"spot_electricity_{user_input.get(CONF_NAME, 'default')}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "Spotové ceny"),
                    data=user_input
                )
            except Exception as e:
                _LOGGER.error(f"Chyba při vytváření konfigurace: {e}")
                errors["base"] = "cannot_connect"

        # Definice konfiguračního schématu
        schema = vol.Schema({
            vol.Required(CONF_NAME, default="Spotové ceny"): str,
            vol.Required(CONF_DISTRIBUTOR): vol.In(REGION),
            vol.Required(CONF_A): str,
            vol.Required(CONF_PRICE_NT, default=1.234): float,
            vol.Required(CONF_PRICE_VT, default=2.345): float,
            vol.Required(CONF_SPOT_PRICE_ENTITY): str,
            vol.Required(CONF_HDO_ENTITY): str,
            vol.Required(CONF_PRODEJ, default=0.35): float,
            vol.Required(CONF_DAN_Z_ELEKTRINY, default=0.03): float,
            vol.Required(CONF_CENA_SYSTEMOVYCH_SLUZEB, default=0.21): float,
            vol.Required(CONF_OZE, default=0.50): float,
            vol.Required(CONF_VYKUP, default=-0.45): float,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=schema, 
            errors=errors
        )