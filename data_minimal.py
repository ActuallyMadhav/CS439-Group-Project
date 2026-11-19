# Minimal loader used to develop view B (owner: Madhav Anantharam).
# Produces the columns view B needs, with the column names from our shared schema,
# so it can be swapped for Saanvi's full data.py without touching the view.
#
# Columns: iso3, country, continent, year, population, gdp, gdp_pc,
#          co2, co2_pc, cons_co2, cons_co2_pc
import geopandas as gpd
import pandas as pd

from selection import YEAR_MIN, YEAR_MAX

# OWID codes that differ from Natural Earth's ADM0_A3
OWID_TO_NE = {'SSD': 'SDS', 'PSE': 'PSX'}
# Natural Earth puts these island states in "Seven seas (open ocean)"
SEVEN_SEAS_FIX = {'MUS': 'Africa', 'SYC': 'Africa', 'MDV': 'Asia', 'SHN': 'Africa'}


def load_world(filename):      # HW3
    return gpd.read_file(filename)


def continent_lookup(world):
    lookup = dict(zip(world['ADM0_A3'], world['CONTINENT']))
    lookup.update(SEVEN_SEAS_FIX)
    return lookup


def load_table(co2_file, map_file):
    raw = pd.read_csv(co2_file)

    # keep real countries only (drops "World", "Asia", "High-income countries", ...)
    is_country = raw['iso_code'].notna() & ~raw['iso_code'].str.startswith('OWID', na=False)
    df = raw[is_country & raw['year'].between(YEAR_MIN, YEAR_MAX)].copy()

    continents = continent_lookup(load_world(map_file))
    df['continent'] = df['iso_code'].map(lambda c: continents.get(OWID_TO_NE.get(c, c)))

    # CO2 is in million tonnes: x 1e6 gives tonnes per person
    df['gdp_pc'] = df['gdp'] / df['population']
    df['co2_pc'] = df['co2'] * 1e6 / df['population']
    df['cons_co2_pc'] = df['consumption_co2'] * 1e6 / df['population']

    df = df.rename(columns={'iso_code': 'iso3', 'consumption_co2': 'cons_co2'})
    return df[['iso3', 'country', 'continent', 'year', 'population', 'gdp', 'gdp_pc',
               'co2', 'co2_pc', 'cons_co2', 'cons_co2_pc']].reset_index(drop=True)
