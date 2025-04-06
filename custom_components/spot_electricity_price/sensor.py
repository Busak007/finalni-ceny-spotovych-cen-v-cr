"""Sensor platform for Spot Electricity Price integration."""
import logging
from datetime import datetime, timedelta
import pytz
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import CONF_NAME



DOMAIN = "spot_electricity_price"
_LOGGER = logging.getLogger(__name__)

# Konstanty pro konfiguraci (shodné s config_flow.py)
CONF_SPOT_PRICE_ENTITY = "spot_price_entity"
CONF_HDO_ENTITY = "hdo_entity"
CONF_PRODEJ = "prodej"
CONF_DAN_Z_ELEKTRINY = "dan_z_elektriny"
CONF_CENA_SYSTEMOVYCH_SLUZEB = "cena_systemovych_sluzeb"
CONF_OZE = "oze"
CONF_VYKUP = "vykup"

CONF_A = "code_a"
CONF_NAME_HDO = "HDO_smart"
CONF_PSC = "psc"
CONF_DISTRIBUTOR = "distributor"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor platform."""
    async_add_entities([ 
        SpotElectricitySensor(config_entry, "Nákup"),
        SpotElectricitySensor(config_entry, "Výkup"),
        SpotElectricitySensor(config_entry, "Součet"),
        SpotElectricitySensor(config_entry, "Distributor"),
        SpotElectricitySensor(config_entry, "Kód elektroměru"),
        SpotElectricitySensor(config_entry, "HDO"),
    ])

class SpotElectricitySensor(SensorEntity):
    """Reprezentace senzoru spot electricity price."""

    def __init__(self, config_entry: ConfigEntry, sensor_type: str):
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._name = f"{config_entry.data.get(CONF_NAME, '')} {sensor_type}"
        self._spot_price_entity = config_entry.data.get(CONF_SPOT_PRICE_ENTITY)
        self._hdo_entity = config_entry.data.get(CONF_HDO_ENTITY)

        # Konfigurace parametrů
        self._prodej = config_entry.data.get(CONF_PRODEJ)
        self._kod_elektromeru = config_entry.data.get(CONF_A)
        self._psc = config_entry.data.get(CONF_PSC)
        self._name_hdo = config_entry.data.get(CONF_NAME_HDO)
        self._distributor = config_entry.data.get(CONF_DISTRIBUTOR)
        
        self._dan_z_elektriny = config_entry.data.get(CONF_DAN_Z_ELEKTRINY)
        self._cena_systemovych_sluzeb = config_entry.data.get(CONF_CENA_SYSTEMOVYCH_SLUZEB)
        self._oze = config_entry.data.get(CONF_OZE)
        self._vykup = config_entry.data.get(CONF_VYKUP)

        self._state = None
        self._attributes = {}

    async def async_update(self):
        """Aktualizace senzoru."""
        try:
            # Získání aktuálních hodnot
            spot_obj = self.hass.states.get(self._spot_price_entity)
            spot_price = float(spot_obj.state) if spot_obj else 0.0
            
            state_obj = self.hass.states.get(self._hdo_entity)
            hdo_state = state_obj.state if state_obj else "unknown"
            hdo_price = float(state_obj.attributes.get("current_price", 0.0)) if state_obj else 0.0

            # Výpočet poplatků
            poplatky = (self._oze + self._cena_systemovych_sluzeb +
                        self._dan_z_elektriny + self._prodej) * 1.21

            if self._sensor_type == "Nákup":
                celkove = spot_price * 1.21 + poplatky + hdo_price
                self._attributes = {
                    "Detaily": {
                        "spotova_cena": f"{round(spot_price, 2)} Kč",
                        "distribuce": f"{round(hdo_price, 2)} Kč",
                        "poplatky": f"{round(poplatky, 2)} Kč",
                        "stav_HDO": hdo_state,
                    },
                    "Distribuce_data": state_obj.attributes.get("HDO_HOURLY", {}) if state_obj else {},
                    "Spot_data": spot_obj.attributes if spot_obj else {}
                }

            elif self._sensor_type == "Výkup":
                celkove = spot_price + self._vykup
                self._attributes = {
                    "Detaily": {
                        "spotova_cena": f"{round(spot_price, 2)} Kč",
                        "vykup": f"{round(self._vykup, 2)} Kč",
                    },
                    "Spot_data": spot_obj.attributes if spot_obj else {}
                }
            elif self._sensor_type == "Distributor":
                self._state = self._distributor
                self._attributes = {
                    "Uzemi": self._distributor
                }

            elif self._sensor_type == "Kód elektroměru":
                self._state = self._kod_elektromeru
                self._attributes = {
                    "Kod": self._kod_elektromeru
                }

            elif self._sensor_type == "HDO":
                self._state = 0
                self._attributes = {
                    "PSC": self._psc,
                    "Kod": self._kod_elektromeru,
                    "Jmeno": self._name_hdo
                }

            elif self._sensor_type == "Součet":
                # Nastavení časové zóny (předpokládám středoevropský čas)
                local_tz = pytz.timezone('Europe/Prague')
                
                # Začátek dne (od půlnoci)
                today_midnight = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Generování dat pro výpočet
                celkove = 0.0
                celkem_data = {}
                
                # Debug výpis - zkontrolujeme strukturu HDO dat
                if state_obj and state_obj.attributes:
                    _LOGGER.info(f"Dostupné atributy HDO: {list(state_obj.attributes.keys())}")
                    
                    # Pokud existuje HDO_HOURLY, vypíšeme jeho struktur
                    if "HDO_HOURLY" in state_obj.attributes:
                        hdo_data = state_obj.attributes.get("HDO_HOURLY", {})
                        _LOGGER.info(f"HDO_HOURLY je typu: {type(hdo_data)}")
                        if isinstance(hdo_data, dict) and hdo_data:
                            sample_key = next(iter(hdo_data))
                            _LOGGER.info(f"Ukázka HDO klíče: {sample_key}, hodnota: {hdo_data[sample_key]}, typ hodnoty: {type(hdo_data[sample_key])}")
                
                # NOVÝ PŘÍSTUP: Použijeme aktuální HDO cenu pro celý den
                # Toto by mělo fungovat i když nerozumíme přesně struktuře HDO_HOURLY
                hourly_data_debug = {}
                
                for hour in range(48):
                    # Generujeme časovou značku ve stejném formátu jako vstupní data
                    time_obj = today_midnight + timedelta(hours=hour)
                    timestamp = time_obj.isoformat()  # Např. '2025-04-05T00:00:00+02:00'
                    
                    # Inicializace hodnot
                    spot_price_value = 0.0
                    
                    # Hledání hodnot spot price
                    if spot_obj and spot_obj.attributes:
                        for spot_ts, spot_val in spot_obj.attributes.items():
                            timestamp_short = timestamp.split("+")[0] if "+" in timestamp else timestamp
                            timestamp_short = timestamp_short.split(".")[0] if "." in timestamp_short else timestamp_short
                            
                            if timestamp in spot_ts or timestamp_short in spot_ts:
                                try:
                                    spot_price_value = float(spot_val) * 1.21
                                    break
                                except (ValueError, TypeError):
                                    _LOGGER.warning(f"Neplatná hodnota spot price pro čas {spot_ts}")
                    
                    # Pro každou hodinu použijeme aktuální HDO cenu
                    # Tím zajistíme, že HDO hodnota nebude nikdy nulová, pokud je k dispozici
                    
                    # Pro debug
                    hourly_data_debug[timestamp] = {
                        "spot_value": spot_price_value, 
                        "hdo_value": hdo_price  # Použijeme aktuální HDO hodnotu pro všechny hodiny
                    }
                    
                    # Výpočet celkové hodnoty
                    total_value = round(spot_price_value + poplatky + hdo_price, 2)
                    celkem_data[timestamp] = total_value
                
                # Zalogujeme pár záznamů pro debug
                _LOGGER.info(f"Debug hodnoty pro první 3 hodiny (nový přístup): {dict(list(hourly_data_debug.items())[:3])}")
                
                # Pokusíme se také získat strukturovaná HDO data přímo (alternativní přístup)
                try:
                    if state_obj and state_obj.attributes and "HDO_HOURLY" in state_obj.attributes:
                        hdo_hourly = state_obj.attributes.get("HDO_HOURLY", {})
                        _LOGGER.info(f"Prvních 5 klíčů HDO_HOURLY: {list(hdo_hourly.keys())[:5]}")
                        
                        if isinstance(hdo_hourly, dict):
                            for k, v in list(hdo_hourly.items())[:5]:
                                _LOGGER.info(f"HDO klíč: {k}, hodnota: {v}")
                except Exception as e:
                    _LOGGER.error(f"Chyba při pokusu o výpis HDO_HOURLY: {e}")

                self._attributes = {
                    "Celkem": celkem_data,
                    "Debug_data": dict(list(hourly_data_debug.items())[:5]),  # Ukládáme 5 záznamů pro kontrolu
                    "Distribuce_data": state_obj.attributes.get("HDO_HOURLY", {}) if state_obj else {},
                    "Spot_data": spot_obj.attributes if spot_obj else {},
                    "Aktualni_HDO_hodnota": hdo_price,  # Přidáme aktuální HDO hodnotu pro debug
                }
                
                # Vypočítat průměrnou celkovou cenu jako stav senzoru
                if celkem_data:
                    celkove = sum(celkem_data.values()) / len(celkem_data)
                else:
                    celkove = 0.0

            else:
                self._attributes = {}
                celkove = 0.0

            self._state = round(celkove, 2)

        except Exception as e:
            _LOGGER.error(f"Chyba při aktualizaci senzoru ({self._sensor_type}): {e}")
            import traceback
            _LOGGER.error(f"Traceback: {traceback.format_exc()}")

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Unique identifier for the sensor."""
        return f"{DOMAIN}_{self._sensor_type.lower()}_{self._name.replace(' ', '_').lower()}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def unit_of_measurement(self):
        return "Kč"

    @property
    def device_class(self):
        return SensorDeviceClass.MONETARY

    @property
    def device_info(self):
        """Vrací informace o zařízení, ke kterému senzor patří."""
        return {
            "identifiers": {(DOMAIN, "spotove_ceny")},
            "name": "Spotové ceny",
            "manufacturer": "@RadekBus",
            "model": "Spotové ceny",
            "entry_type": "service",
        }
