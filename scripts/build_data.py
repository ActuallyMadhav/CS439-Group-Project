"""Run after scripts/download_data.py to build the shared table."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import export_table
root = Path(__file__).resolve().parents[1]
raw = root / 'data' / 'raw'
df = export_table(raw / 'owid-co2-data.csv', raw / 'owid-energy-data.csv',
                  raw / 'ne_50m_admin_0_countries.geojson', root / 'data' / 'processed' / 'shared_table.csv')
print(f'Rows: {len(df):,}; country codes (excluding World): {df.loc[df.iso3 != "OWID_WRL", "iso3"].nunique()}')
print(f'Years: {df.year.min()}–{df.year.max()}; duplicate country-years: {df.duplicated(["iso3", "year"]).sum()}')
