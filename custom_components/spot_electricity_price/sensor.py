"""Sensor platform for Spot Electricity Price integration."""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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
        self._state = None
        self._attributes = {}

    def _conf(self, key, default=None):
        """Číst konfiguraci — nejdříve z options, pak z data."""
        return self._config_entry.options.get(
            key, self._config_entry.data.get(key, default)
        )

    @property
    def name(self):
        config_name = self._conf(CONF_NAME, "Spotové ceny")
        return f"{config_name} {self._sensor_type}"

    @property
    def unique_id(self):
        """Unique identifier for the sensor."""
        config_name = self._conf(CONF_NAME, "Spotové ceny")
        return f"{DOMAIN}_{self._sensor_type.lower()}_{config_name.replace(' ', '_').lower()}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def unit_of_measurement(self):
        if self._sensor_type == "Distributor":
            return None
        return "Kč/kWh"

    @property
    def device_class(self):
        if self._sensor_type == "Distributor":
            return None
        return SensorDeviceClass.MONETARY

    @property
    def device_info(self):
        """Vrací informace o zařízení."""
        return {
            "identifiers": {(DOMAIN, "spotove_ceny")},
            "name": "Spotové ceny",
            "manufacturer": "RadekBus",
            "model": "Spotové ceny",
            "entry_type": "service",
        }

    def _compute_hdo_hourly(self, state_obj, now: datetime, price_nt: float, price_vt: float) -> dict:
        """Vypočítat hodinové HDO ceny pro 48 hodin na základě HDO entita atributů."""
        hdo_data = {}
        if not state_obj:
            return hdo_data

        hdo_raw_times = state_obj.attributes.get("HDO Times", "")
        nt_ranges = []
        for period in hdo_raw_times.split(","):
            try:
                start_str, end_str = period.strip().split("-")
                nt_ranges.append((int(start_str.strip()), int(end_str.strip())))
            except ValueError:
                continue

        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(48):
            time_point = midnight + timedelta(hours=i)
            hour = time_point.hour
            price = price_vt
            for start, end in nt_ranges:
                if start <= hour < end:
                    price = price_nt
                    break
            hdo_data[time_point.isoformat()] = float(price)

        return hdo_data

    async def async_update(self):
        """Aktualizace senzoru."""
        try:
            local_tz = ZoneInfo(self.hass.config.time_zone)
            # Lokální čas jako naivní datetime pro konzistenci s generovanými timestampy
            now = datetime.now(tz=local_tz).replace(tzinfo=None)

            spot_price_entity = self._conf(CONF_SPOT_PRICE_ENTITY)
            hdo_entity_id = self._conf(CONF_HDO_ENTITY)
            price_nt = float(self._conf(CONF_PRICE_NT, 0.0))
            price_vt = float(self._conf(CONF_PRICE_VT, 0.0))
            prodej = float(self._conf(CONF_PRODEJ, 0.0))
            dan_z_elektriny = float(self._conf(CONF_DAN_Z_ELEKTRINY, 0.0))
            cena_systemovych_sluzeb = float(self._conf(CONF_CENA_SYSTEMOVYCH_SLUZEB, 0.0))
            oze = float(self._conf(CONF_OZE, 0.0))
            vykup = float(self._conf(CONF_VYKUP, 0.0))

            spot_obj = self.hass.states.get(spot_price_entity) if spot_price_entity else None
            hdo_obj = self.hass.states.get(hdo_entity_id) if hdo_entity_id else None

            if spot_obj is None and self._sensor_type not in ("Distributor", "HDO"):
                _LOGGER.warning("Entita spotové ceny '%s' nenalezena", spot_price_entity)

            spot_price = 0.0
            if spot_obj and spot_obj.state not in ("unknown", "unavailable", None):
                try:
                    spot_price = float(spot_obj.state)
                except (ValueError, TypeError):
                    _LOGGER.warning("Neplatný stav entity spotové ceny: %s", spot_obj.state)

            hdo_state = hdo_obj.state if hdo_obj else "unknown"
            hdo_price = 0.0
            if hdo_obj:
                try:
                    hdo_price = float(hdo_obj.attributes.get("current_price", 0.0))
                except (ValueError, TypeError):
                    pass

            # Výpočet poplatků (bez DPH × 1,21)
            poplatky = (oze + cena_systemovych_sluzeb + dan_z_elektriny + prodej) * 1.21

            if self._sensor_type == "Nákup":
                celkove = spot_price * 1.21 + poplatky + hdo_price
                self._attributes = {
                    "Detaily": {
                        "spotova_cena": round(spot_price, 4),
                        "distribuce": round(hdo_price, 4),
                        "poplatky": round(poplatky, 4),
                        "stav_HDO": hdo_state,
                    },
                    "Distribuce_data": hdo_obj.attributes.get("HDO_HOURLY", {}) if hdo_obj else {},
                    "Spot_data": dict(spot_obj.attributes) if spot_obj else {},
                }

            elif self._sensor_type == "Výkup":
                celkove = spot_price + vykup
                vykup_data = {}
                if spot_obj and spot_obj.attributes:
                    for timestamp, value in spot_obj.attributes.items():
                        try:
                            vykup_data[timestamp] = round(float(value) + vykup, 4)
                        except (ValueError, TypeError):
                            pass
                self._attributes = {
                    "Detaily": {
                        "spotova_cena": round(spot_price, 4),
                        "vykup": round(vykup, 4),
                    },
                    "Spot_data": dict(spot_obj.attributes) if spot_obj else {},
                    "Vykup_data": vykup_data,
                }

            elif self._sensor_type == "Distributor":
                distributor = self._conf(CONF_DISTRIBUTOR, "")
                self._state = distributor
                self._attributes = {"Uzemi": distributor}
                return

            elif self._sensor_type == "HDO":
                if hdo_obj and hdo_obj.state == "on":
                    celkove = price_nt
                else:
                    celkove = price_vt

                hourly_prices = self._compute_hdo_hourly(hdo_obj, now, price_nt, price_vt)
                hdo_raw_times = hdo_obj.attributes.get("HDO Times", "") if hdo_obj else ""

                self._attributes = {
                    "PSC": self._conf(CONF_PSC, ""),
                    "Kod": self._conf(CONF_A, ""),
                    "Cena NT": price_nt,
                    "Cena VT": price_vt,
                    "Časy HDO Od Do": hdo_raw_times,
                    "Aktuálně": hdo_state,
                    "hodinove_ceny": hourly_prices,
                }

            elif self._sensor_type == "Součet":
                # Normalizace spot dat na lokální naivní timestampy
                spot_data = {}
                if spot_obj and spot_obj.attributes:
                    for timestamp, value in spot_obj.attributes.items():
                        try:
                            dt = datetime.fromisoformat(str(timestamp))
                            if dt.tzinfo is not None:
                                dt = dt.astimezone(local_tz).replace(tzinfo=None)
                            spot_data[dt.isoformat()] = float(value)
                        except (ValueError, TypeError):
                            pass

                # HDO hodinové ceny — vypočítáme přímo z HDO entity
                hdo_data = self._compute_hdo_hourly(hdo_obj, now, price_nt, price_vt)

                # Kombinace spot + HDO + poplatky pro všechny dostupné hodiny
                celkem_data = {}
                all_timestamps = set(spot_data.keys()) | set(hdo_data.keys())
                for timestamp in sorted(all_timestamps):
                    spot_raw = spot_data.get(timestamp, 0.0)
                    hdo_cena = hdo_data.get(timestamp, 0.0)
                    celkem_data[timestamp] = round(spot_raw * 1.21 + hdo_cena + poplatky, 4)

                # Aktuální cena pro aktuální hodinu
                current_ts = now.replace(minute=0, second=0, microsecond=0).isoformat()
                aktualni = celkem_data.get(current_ts, 0.0)
                celkove = round(aktualni, 2)

                self._attributes = {
                    "Celkem": celkem_data,
                    "Spot_data": dict(spot_obj.attributes) if spot_obj else {},
                    "HDO_data": hdo_data,
                    "Poplatky": round(poplatky, 4),
                    "Aktualni_cas": current_ts,
                    "Aktualni_celkova_cena": celkove,
                }

            else:
                self._attributes = {}
                celkove = 0.0

            self._state = round(celkove, 2)

        except Exception as e:
            _LOGGER.error("Chyba při aktualizaci senzoru (%s): %s", self._sensor_type, e, exc_info=True)
