# Saanvi: data pipeline and View E

## Install and download

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_data.py
```

## Build and check shared data

```bash
python scripts/build_data.py
python -m unittest discover -s tests -p 'test_data_e.py'     # synthetic + real row counts
QT_QPA_PLATFORM=offscreen python tests/test_part_e.py data/raw/owid-co2-data.csv data/raw/ne_50m_admin_0_countries.geojson
```

## Run View E

```bash
python main_e.py -i data/raw/owid-co2-data.csv -e data/raw/owid-energy-data.csv -m data/raw/ne_50m_admin_0_countries.geojson
```

To show a country or save a figure:

```bash
python main_e.py -i data/raw/owid-co2-data.csv -e data/raw/owid-energy-data.csv -m data/raw/ne_50m_admin_0_countries.geojson --select GBR
python main_e.py -i data/raw/owid-co2-data.csv -e data/raw/owid-energy-data.csv -m data/raw/ne_50m_admin_0_countries.geojson --select GBR --screenshot view_e_gbr.png
```

## Integrate in the team's final window

```python
from data import load_table
from views.fuel_mix_view import FuelMixPanel

# Reuse the SAME SelectionModel object shared by the other views.
df = load_table(co2_file, map_file, energy_file)
fuel_panel = FuelMixPanel(model)
layout.addWidget(fuel_panel)
fuel_panel.draw(df)
```

`data.py` keeps the column names expected by the map and bubble charts. It also
returns the World as iso3 `OWID_WRL` (continent empty); views that plot countries
filter it out by continent. `main.py` already places View E in the team window.

## Limitations / follow-up checks

- The OWID data files are not in the repository (data/raw is gitignored); `scripts/download_data.py` fetches the current versions. The real-data tests check the current release: 223 countries + World, 1990–2022, every country-year present.
- CO2-by-fuel stack includes coal, oil, gas, cement and flaring. It may not sum exactly to the published CO2 total because of other sources or revisions.
- World is a dedicated OWID_WRL record, not a sum of the retained country rows.
- When multiple countries are selected, View E initially displays the first; the dropdown lets you choose among selected countries. The choice is local to View E and does not change the shared selection.
- View E follows selection and selected year; basis and continent are not applicable to the fuel-specific historical series.
