# Did Rich Countries Really Cut Their Emissions?

CS 43900 Fall 2026 final project: Madhav Anantharam, Shloka Kandukuri, Shivam Rastogi,
Tanisha Phadke and Saanvi Khemka.

Five linked Matplotlib views in one PyQt5 window. They compare **territorial** CO₂
(emitted inside a country's borders) with **consumption-based** CO₂ (the CO₂ caused by
what a country consumes, including imports) for every country, 1990–2022.

| View | Owner | Module | Stand-alone window |
|---|---|---|---|
| A. World map (choropleth) | Shloka | `views/map_view.py` | `main_a.py` |
| B. Wealth vs emissions (bubble chart) | Madhav | `views/bubble_view.py` | `main_b.py` |
| C. Decoupling (indexed small multiples) | Shivam | `views/decoupling_view.py` | `main_c.py` |
| D. Outsourced emissions (scatter with y = x) | Tanisha | `views/outsourcing_view.py` | `main_d.py` |
| E. Fuel and electricity mix (stacked area) | Saanvi | `views/fuel_mix_view.py` | `main_e.py` |

| Shared component | Owner | Module |
|---|---|---|
| Selection model and view contract | Madhav | `selection.py` (and `ControlBar` in `main_b.py`) |
| Map geometry and country-code matching | Shloka | `map_geometry.py` |
| Derived metrics (1990 = 100, growth, decoupling) | Shivam | `metrics.py` |
| Tooltip and highlight style | Tanisha | `tooltip.py` |
| Data pipeline | Saanvi | `data.py`, `scripts/build_data.py` |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_data.py      # OWID CO2 + energy data and Natural Earth map -> data/raw/
```

## Run

```bash
D=data/raw
# all five linked views
python main.py -i $D/owid-co2-data.csv -m $D/ne_50m_admin_0_countries.geojson
# optional: --year 2008 --basis consumption --continent Europe --select GBR,SWE,USA,CHN
#           --screenshot all_views.png      (saves the whole window and exits)

# one view at a time (same flags)
python main_d.py -i $D/owid-co2-data.csv -m $D/ne_50m_admin_0_countries.geojson --select GBR,CHN
```

`main.py` and `main_d.py` find `owid-energy-data.csv` next to the CO₂ file; pass
`-e <file>` to use another path. `main_e.py` needs `-e`.

How the linking works: every view implements `draw(df)` (once) and
`update_view(state)` (on every change) and listens to one `SelectionModel`. The
control bar sets year, basis and continent. Clicking countries on the map (A) or
clicking/brushing bubbles (B) sets the selection, and every view redraws from it.

## Tests

Headless; set `QT_QPA_PLATFORM=offscreen` (PowerShell: `$env:QT_QPA_PLATFORM='offscreen'`).

```bash
python -m unittest discover -s tests -p 'test_data_e.py'                  # pipeline + row counts
python tests/test_part_a.py $D/owid-co2-data.csv $D/ne_50m_admin_0_countries.geojson
python tests/test_part_b.py $D/owid-co2-data.csv $D/ne_50m_admin_0_countries.geojson
python tests/test_metrics.py $D/owid-co2-data.csv $D/ne_50m_admin_0_countries.geojson
python tests/test_part_c.py $D/owid-co2-data.csv $D/ne_50m_admin_0_countries.geojson
python tests/test_part_d.py $D/owid-co2-data.csv $D/ne_50m_admin_0_countries.geojson
python tests/test_part_e.py $D/owid-co2-data.csv $D/ne_50m_admin_0_countries.geojson
```

On Windows, also set `PYTHONIOENCODING=utf-8` so the tests can print `CO₂` and `→`.
Take report screenshots without `offscreen`: Qt's offscreen platform does not draw
widget text.

## Data notes

- Current OWID release: 223 countries + World, 1990–2022 (GDP ends in 2022 and
  consumption-based CO₂ starts in 1990). About 120 countries have consumption-based
  estimates; the others are shown grey or left out with a note.
- Seven small territories (Guadeloupe, Martinique, French Guiana, Réunion, Mayotte,
  Bonaire, Christmas Island) are drawn by Natural Earth as part of France, the
  Netherlands or Australia. They get a continent by hand (`data.py`) but no map shape.
