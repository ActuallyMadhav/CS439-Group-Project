"""Tests for the shared data pipeline (owner: Saanvi Khemka).

PipelineTests use tiny synthetic OWID inputs. RealDataTests check row counts on
the real files in data/raw (run scripts/download_data.py first; skipped otherwise).

    python -m unittest discover -s tests -p 'test_data_e.py'
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from data import WORLD, build_table, load_table
from selection import CONTINENTS, YEAR_MAX, YEAR_MIN

RAW = Path(__file__).resolve().parents[1] / 'data' / 'raw'
CO2, ENERGY, MAP = (RAW / 'owid-co2-data.csv', RAW / 'owid-energy-data.csv',
                    RAW / 'ne_50m_admin_0_countries.geojson')


class PipelineTests(unittest.TestCase):
    def test_merge_and_world(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pd.DataFrame([
                dict(iso_code='USA', country='United States', year=2022, population=100, gdp=1000, co2=2, consumption_co2=3, coal_co2=1, oil_co2=1),
                dict(iso_code='OWID_WRL', country='World', year=2022, population=200, gdp=2000, co2=5, consumption_co2=6, coal_co2=3, oil_co2=2),
                dict(iso_code='OWID_EUR', country='Europe', year=2022, population=100, gdp=1000, co2=2, consumption_co2=2),
            ]).to_csv(root / 'co2.csv', index=False)
            pd.DataFrame([dict(iso_code='USA', year=2022, low_carbon_share_elec=40),
                          dict(iso_code='OWID_WRL', year=2022, low_carbon_share_elec=50)]).to_csv(root / 'energy.csv', index=False)
            with patch('data.load_world', return_value=pd.DataFrame({'ADM0_A3':['USA'], 'CONTINENT':['North America']})):
                df = build_table(root / 'co2.csv', root / 'energy.csv', root / 'map.geojson')
            self.assertEqual(len(df), 2)
            self.assertEqual(df.loc[df.iso3 == 'USA', 'co2_pc'].iloc[0], 20000)
            self.assertEqual(df.loc[df.iso3 == 'USA', 'low_carbon_share_elec'].iloc[0], 40)
            self.assertIn('OWID_WRL', df.iso3.values)


@unittest.skipUnless(CO2.exists() and ENERGY.exists() and MAP.exists(), 'data/raw not downloaded')
class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_table(CO2, MAP, ENERGY)

    def test_row_counts(self):
        df = self.df
        countries = df.loc[df.iso3 != WORLD, 'iso3'].nunique()
        years = YEAR_MAX - YEAR_MIN + 1
        print(f'\nshared table: {len(df):,} rows, {countries} countries + World, {years} years')
        # the proposal counted 218 countries; OWID adds a few small territories over time
        self.assertGreaterEqual(countries, 218)
        self.assertEqual(len(df), (countries + 1) * years)          # every country-year present
        self.assertEqual((df.year.min(), df.year.max()), (YEAR_MIN, YEAR_MAX))
        self.assertFalse(df.duplicated(['iso3', 'year']).any())
        aggregates = df.iso3.str.startswith('OWID') & (df.iso3 != WORLD)   # "Asia", "High-income", ...
        self.assertFalse(aggregates.any())

    def test_world_and_continents(self):
        df = self.df
        self.assertEqual(len(df[df.iso3 == WORLD]), YEAR_MAX - YEAR_MIN + 1)
        self.assertTrue(df[df.iso3 == WORLD].continent.isna().all())
        countries = df[df.iso3 != WORLD]
        self.assertTrue(countries.continent.isin(CONTINENTS + ('Antarctica',)).all(),
                        countries.loc[~countries.continent.isin(CONTINENTS), 'iso3'].unique())

    def test_columns_and_units(self):
        df = self.df
        for col in ('iso3', 'country', 'continent', 'year', 'population', 'gdp', 'gdp_pc', 'co2',
                    'co2_pc', 'cons_co2', 'cons_co2_pc', 'net_imported_co2', 'coal_co2',
                    'low_carbon_share_elec'):
            self.assertIn(col, df.columns)
        gbr = df[(df.iso3 == 'GBR') & (df.year == 2022)].iloc[0]
        self.assertTrue(3 < gbr.co2_pc < 6, gbr.co2_pc)              # tonnes per person
        self.assertTrue(0 < gbr.low_carbon_share_elec <= 100)
        # consumption-based CO2 exists for about 120 countries
        has_cons = df[(df.year == 2022) & (df.iso3 != WORLD)].cons_co2.notna().sum()
        self.assertTrue(110 <= has_cons <= 130, has_cons)


if __name__ == '__main__':
    unittest.main()
