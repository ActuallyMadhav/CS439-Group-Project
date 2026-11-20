"""Lightweight tests using tiny synthetic OWID inputs."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from data import build_table


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


if __name__ == '__main__':
    unittest.main()
