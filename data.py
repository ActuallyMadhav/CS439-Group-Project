"""Shared country-year table for all five views (1990–2022)."""
from pathlib import Path
import pandas as pd
import geopandas as gpd

YEAR_MIN, YEAR_MAX = 1990, 2022

def load_world(filename):
    return gpd.read_file(filename)

def continent_lookup(world):
    lookup = dict(zip(world["ADM0_A3"], world["CONTINENT"]))
    lookup.update({"MUS": "Africa", "SYC": "Africa", "MDV": "Asia", "SHN": "Africa"})
    return lookup

FUEL_COLUMNS = ('coal_co2', 'oil_co2', 'gas_co2', 'cement_co2', 'flaring_co2')
ENERGY_COLUMNS = ('low_carbon_share_elec', 'coal_share_elec', 'gas_share_elec',
                  'nuclear_share_elec', 'hydro_share_elec', 'solar_share_elec', 'wind_share_elec')


def build_table(co2_file, energy_file, map_file):
    co2 = pd.read_csv(co2_file, low_memory=False)
    valid = co2.iso_code.notna() & co2.iso_code.str.fullmatch(r'[A-Z]{3}', na=False)
    valid &= co2.year.between(YEAR_MIN, YEAR_MAX)
    countries = co2.loc[valid].copy()
    # Preserve World separately for View E.
    # Recent OWID datasets have a missing ISO code for World.
    world = co2.loc[
        (co2["country"] == "World") &
        co2["year"].between(YEAR_MIN, YEAR_MAX)
    ].copy()

    # Assign a consistent identifier for World.
    world["iso_code"] = "OWID_WRL"

    # Combine individual countries and World.
    df = pd.concat([countries, world], ignore_index=True)
    if df.duplicated(['iso_code', 'year']).any():
        raise ValueError('Duplicate country/year rows in CO2 source')

    lookup = continent_lookup(load_world(map_file))
    df['continent'] = df.iso_code.map(lambda code: lookup.get({'SSD': 'SDS', 'PSE': 'PSX'}.get(code, code)))
    df['gdp_pc'] = df.gdp / df.population.replace(0, float('nan'))
    df['co2_pc'] = df.co2 * 1e6 / df.population.replace(0, float('nan'))
    df['cons_co2_pc'] = df.consumption_co2 * 1e6 / df.population.replace(0, float('nan'))
    df['net_imported_co2'] = df.consumption_co2 - df.co2
    df = df.rename(columns={'iso_code': 'iso3', 'consumption_co2': 'cons_co2'})

    energy = pd.read_csv(energy_file, low_memory=False)
    # Energy data identifies countries using iso_code in recent OWID releases.
    if 'iso_code' not in energy.columns:
        raise ValueError('Energy dataset must contain iso_code; inspect your OWID file version')
    fields = [c for c in ENERGY_COLUMNS if c in energy.columns]
    if 'low_carbon_share_elec' not in fields:
        raise ValueError('Energy dataset missing low_carbon_share_elec')
   # Handle World rows when the country column is available.
    # The smaller test dataset may not contain this column.
    if 'country' in energy.columns:
        energy.loc[
            energy['country'] == 'World',
            'iso_code'
        ] = 'OWID_WRL'

    # Keep only the columns needed for the merge.
    energy = energy.loc[:, ['iso_code', 'year'] + fields].copy()

    # Rename ISO code to match the shared table.
    energy = energy.rename(columns={'iso_code': 'iso3'})

    energy = energy[
        energy['iso3'].notna() &
        energy['year'].between(YEAR_MIN, YEAR_MAX)
    ]

    
    if energy.duplicated(['iso3', 'year']).any():
        raise ValueError('Duplicate country/year rows in energy source')
    df = df.merge(energy, on=['iso3', 'year'], how='left', validate='one_to_one')
    return df.sort_values(['iso3', 'year']).reset_index(drop=True)


def load_table(co2_file, map_file, energy_file=None):
    """Compatible with existing main_b.py's two-argument load_table call."""
    if energy_file is None:
        energy_file = Path(co2_file).with_name('owid-energy-data.csv')
    return build_table(co2_file, energy_file, map_file)


def export_table(co2_file, energy_file, map_file, output):
    df = build_table(co2_file, energy_file, map_file)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df
