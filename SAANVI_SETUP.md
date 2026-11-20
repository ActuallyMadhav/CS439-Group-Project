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
python -m unittest discover -s tests -p 'test_data_e.py'
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

`data.py` retains the column names expected by the existing map and bubble charts.

## Git workflow (from your cloned repository)

Copy the new files into the clone. Then:

```bash
git switch -c saanvi-data-view-e
git status
git add data.py main_e.py scripts/build_data.py views/fuel_mix_view.py tests/test_data_e.py SAANVI_SETUP.md
git commit -m "Add shared OWID data pipeline and fuel mix View E"
git push -u origin saanvi-data-view-e
```

Open a pull request into main. Don't overwrite teammates' files or push directly to main without coordinating.

## Limitations / follow-up checks

- The actual OWID data files are not included in the uploaded ZIP; validate against downloaded current source files.
- CO2-by-fuel stack includes coal, oil, gas, cement and flaring. It may not sum exactly to the published CO2 total because of other sources or revisions.
- World is a dedicated OWID_WRL record, not a sum of the retained country rows.
- When multiple countries are selected, View E initially displays the first; the dropdown lets you choose among selected countries.
- View E follows selection and selected year; basis and continent are not applicable to the fuel-specific historical series.
