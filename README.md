# Spotové ceny pro Home Assistant

Tato integrace umožňuje sledovat spotové ceny elektřiny v kombinaci s HDO tarifem.

## Instalace

### HACS (doporučeno)
1. Zajistěte, že máte nainstalovaný [HACS](https://hacs.xyz/)
2. Přejděte do HACS > Integrace > Nabídka (tři tečky v pravém horním rohu) > Vlastní repozitáře
3. Přidejte URL tohoto repozitáře
4. Klikněte na "Stáhnout"
5. Restartujte Home Assistant

### Ruční instalace
1. Stáhněte si nejnovější verzi z GitHubu
2. Rozbalte soubor a zkopírujte složku `custom_components/spot_electricity_price` do složky `custom_components` ve vaší instalaci Home Assistant
3. Restartujte Home Assistant

## Konfigurace

Po instalaci přidejte integraci přes Nastavení > Zařízení a služby > Integrace > Přidat integraci > Spotové ceny

### Požadované parametry:
- Název: Název integrace (výchozí: Spotové ceny)
- Distributor: Váš distributor elektřiny (EG.D, ČEZ, PRE) - pro budoucí implementaci v rámci jedné integrace
- Kód elektroměru: Kód elektroměru pro HDO - pro budoucí implementaci v rámci jedné integrace
- Cena NT: Cena v nízkém tarifu (včetně DPH)
- Cena VT: Cena ve vysokém tarifu (včetně DPH)
- Entita spotové ceny: Entita poskytující spotové ceny (bez DPH)
- HDO entita: Entita poskytující informace o HDO (bez DPH)
- Další parametry pro výpočet ceny elektřiny (bez DPH)


## Přidání grafu do lovelace 
![electricity prices graph](docs/lovelace_graf.png)
```
type: custom:apexcharts-card
header:
  show: true
  show_states: true
  colorize_states: true
graph_span: 2d
stacked: false
span:
  start: day
  offset: +0d
now:
  show: true
  label: Nyní
  color: green
series:
  - entity: sensor.soucet
    name: Nákup
    color: orange
    type: column
    group_by:
      func: max
      duration: 1hour
    unit: Kč/kWh
    data_generator: >
      return  Object.entries(entity.attributes.Celkem).map(([date, value],
      index) => {
        return [new Date(date).getTime(), value];
      });
  - entity: sensor.vykup
    name: Výkup
    color: green
    type: line
    group_by:
      func: max
      duration: 1hour
    unit: Kč/kWh
    data_generator: >
      return  Object.entries(entity.attributes.Spot_data).map(([date, value],
      index) => {
        return [new Date(date).getTime(), value];
      });
```

