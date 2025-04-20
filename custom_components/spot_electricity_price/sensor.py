"""Sensor platform for Spot Electricity Price integration."""
import logging
import pytz
from datetime import datetime, timedelta
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
CONF_PRICE_VT = "price_vt"
CONF_PRICE_NT = "price_nt"

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
        self._price_vt = config_entry.data.get(CONF_PRICE_VT)
        self._price_nt = config_entry.data.get(CONF_PRICE_NT)
        
        self._dan_z_elektriny = config_entry.data.get(CONF_DAN_Z_ELEKTRINY)
        self._cena_systemovych_sluzeb = config_entry.data.get(CONF_CENA_SYSTEMOVYCH_SLUZEB)
        self._oze = config_entry.data.get(CONF_OZE)
        self._vykup = config_entry.data.get(CONF_VYKUP)

        self._state = None
        self._attributes = {}

    async def async_update(self):
        """Aktualizace senzoru."""
        now = datetime.now()
        
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
                
                # Vytvoříme slovník pro hodinové výkupní ceny
                vykup_data = {}
                
                # Zpracování dat ze spotových cen s přidáním výkupní ceny
                if spot_obj and spot_obj.attributes:
                    for timestamp, value in spot_obj.attributes.items():
                        try:
                            spot_value = float(value)
                            vykup_value = spot_value + self._vykup
                            vykup_data[timestamp] = round(vykup_value, 2)
                        except (ValueError, TypeError):
                            _LOGGER.warning(f"Neplatná hodnota spot price pro čas {timestamp}")
                            
                self._attributes = {
                    "Detaily": {
                        "spotova_cena": f"{round(spot_price, 2)} Kč",
                        "vykup": f"{round(self._vykup, 2)} Kč",
                    },
                    "Spot_data": spot_obj.attributes if spot_obj else {},
                    "Vykup_data": vykup_data
                }

            elif self._sensor_type == "Distributor":
                celkove = 0
                self._state = self._distributor
                self._attributes = {
                    "Uzemi": self._distributor
                }

            elif self._sensor_type == "HDO":
                state_obj = self.hass.states.get(self._hdo_entity)
                if state_obj and state_obj.state == "on":
                    celkove = self._price_nt
                else:
                    celkove = self._price_vt

                # Parsování HDO časů
                hdo_raw_times = state_obj.attributes.get("HDO Times", "")
                nt_ranges = []
                for period in hdo_raw_times.split(","):
                    try:
                        start_str, end_str = period.strip().split("-")
                        start_hour = int(start_str.strip())
                        end_hour = int(end_str.strip())
                        nt_ranges.append((start_hour, end_hour))
                    except ValueError:
                        continue

                # Vygenerování timestampů pro následujících 48 hodin
                midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                hourly_prices = {}

                for i in range(48):
                    time_point = midnight + timedelta(hours=i)
                    hour = time_point.hour
                    price = self._price_vt  # výchozí VT

                    for start, end in nt_ranges:
                        if start <= hour < end:
                            price = self._price_nt
                            break

                    hourly_prices[time_point.isoformat()] = price

                self._attributes = {
                    "PSC": self._psc,
                    "Kod": self._kod_elektromeru,
                    "Cena NT": self._price_nt,
                    "Cena VT": self._price_vt,
                    "Časy HDO Od Do": hdo_raw_times,
                    "Aktuálně": state_obj.state,
                    "hodinove_ceny": hourly_prices,
                }

            elif self._sensor_type == "Součet":
                # Získání dat ze spotových cen
                spot_data = {}
                if spot_obj and spot_obj.attributes:
                    for timestamp, value in spot_obj.attributes.items():
                        try:
                            # Normalizace timestampu (odstraníme timezone)
                            dt = datetime.fromisoformat(timestamp)
                            naive_ts = dt.replace(tzinfo=None).isoformat()
                            spot_data[naive_ts] = float(value)
                        except (ValueError, TypeError):
                            _LOGGER.warning(f"Neplatná hodnota spot price pro čas {timestamp}")
                            continue

                # Získání dat z HDO cen (z entity sensor.hdo)
                hdo_entity = self.hass.states.get('sensor.hdo')
                hdo_data = {}
                if hdo_entity and 'hodinove_ceny' in hdo_entity.attributes:
                    for timestamp, value in hdo_entity.attributes['hodinove_ceny'].items():
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            naive_ts = dt.replace(tzinfo=None).isoformat()
                            hdo_data[naive_ts] = float(value)
                        except Exception:
                            continue


                # Vytvoření společného slovníku s výslednými cenami
                celkem_data = {}
                
                # Projdeme všechny časové značky, které máme k dispozici
                all_timestamps = set(spot_data.keys()).union(set(hdo_data.keys()))
                
                for timestamp in sorted(all_timestamps):
                    spot_raw = spot_data.get(timestamp, 0.0)
                    hdo_cena = hdo_data.get(timestamp, 0.0)

                    # Skutečný výpočet až na konci
                    spot_s_dph = spot_raw * 1.21
                    celkem = spot_s_dph + hdo_cena + poplatky

                    celkem_data[timestamp] = round(celkem, 4)  # nebo 5–6 pro vyšší přesnost


                # Aktuální cena - vezmeme nejbližší hodinu
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                current_timestamp = current_hour.isoformat()
                
                # Najdeme aktuální cenu
                aktualni_celkova_cena = celkem_data.get(current_timestamp, 0.0)
                celkove = round(aktualni_celkova_cena, 2)

                # Příprava atributů
                self._attributes = {
                    "Celkem": celkem_data,
                    "Spot_data": spot_obj.attributes if spot_obj else {},
                    "HDO_data": hdo_data,
                    "Poplatky": round(poplatky, 2),
                    "Aktualni_cas": current_timestamp,
                    "Aktualni_celkova_cena": celkove,
                    "Debug": {
                        "Spot_raw": spot_data.get(current_timestamp, 0.0),
                        "Spot_s_dph": round(spot_data.get(current_timestamp, 0.0) * 1.21, 6),
                        "HDO": hdo_data.get(current_timestamp, 0.0),
                        "Poplatky": round(poplatky, 6),
                        "Součet_před_zaokrouhlením": (
                            spot_data.get(current_timestamp, 0.0) * 1.21 +
                            hdo_data.get(current_timestamp, 0.0) +
                            poplatky
                        ),
                    }
                }



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
