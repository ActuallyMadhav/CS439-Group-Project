"""Derived metrics shared by the team (owner: Shivam Rastogi).

Pure pandas, no GUI code, so any view (or a findings script) can use it.
Input is the tidy table from data_minimal.load_table / Saanvi's data.py with the
shared column names:
    iso3, country, continent, year, population, gdp, gdp_pc,
    co2, co2_pc, cons_co2, cons_co2_pc

    df = add_metrics(df)            # adds every column below, returns a copy

Columns added
    <col>_idx          each series indexed to its 1990 value = 100, for
                       gdp, co2, cons_co2, gdp_pc, co2_pc, cons_co2_pc.
                       NaN when the country has no (positive) 1990 value.
    <col>_cagr         compound annual growth since 1990 (0.02 = 2 %/year),
                       for gdp, co2, cons_co2. NaN in 1990 itself.
    <col>_yoy          growth over the previous year, for gdp, co2, cons_co2.
    decoupled_terr     True when GDP grew at least MIN_GDP_GROWTH since 1990
    decoupled_cons     while territorial / consumption CO2 is below its 1990 level
    decoupled_both     ("absolute decoupling"). NaN-safe: missing data -> False.

Decoupling rule (written down for the report)
    A country is *absolutely decoupled* in year Y on a basis when
        gdp_idx >= 100 * (1 + MIN_GDP_GROWTH)   (its economy really grew)
        co2_idx  < 100                          (its emissions fell below 1990)
    It is *relatively decoupled* when emissions rose, but more slowly than GDP.
    Totals are used, not per-person values: the planet only cares about the total.
"""
import numpy as np
import pandas as pd

BASE_YEAR = 1990
MIN_GDP_GROWTH = 0.10        # GDP must be >= 10 % above 1990 to count as "grew"

INDEX_COLS = ('gdp', 'co2', 'cons_co2', 'gdp_pc', 'co2_pc', 'cons_co2_pc')
GROWTH_COLS = ('gdp', 'co2', 'cons_co2')
BASIS_COL = {'territorial': 'co2', 'consumption': 'cons_co2'}

# summary categories (Q1)
BOTH = 'Decoupled on both bases'
TERR_ONLY = 'Territorial only (cut partly moved abroad)'
CONS_ONLY = 'Consumption only'
NEITHER = 'Not decoupled'
NO_CONS = 'No consumption estimate'
CATEGORY_ORDER = (BOTH, TERR_ONLY, CONS_ONLY, NEITHER, NO_CONS)


def _base_values(df, col, base_year=BASE_YEAR):
    """Each country's base-year value of `col`, aligned to df's rows (NaN if missing or <= 0)."""
    base = df.loc[df['year'] == base_year].set_index('iso3')[col]
    base = base.where(base > 0)
    return df['iso3'].map(base)


def add_indexed(df, cols=INDEX_COLS, base_year=BASE_YEAR):
    """Add <col>_idx = 100 * value / value in base_year, per country."""
    out = df.copy()
    for col in cols:
        out[f'{col}_idx'] = 100.0 * out[col] / _base_values(out, col, base_year)
    return out


def add_growth(df, cols=GROWTH_COLS, base_year=BASE_YEAR):
    """Add <col>_cagr (compound annual growth since base_year) and <col>_yoy."""
    out = df.sort_values(['iso3', 'year']).copy()
    years = (out['year'] - base_year).astype(float)
    years = years.where(years > 0)
    for col in cols:
        ratio = out[col] / _base_values(out, col, base_year)
        cagr = np.power(ratio.where(ratio > 0), 1.0 / years) - 1.0
        out[f'{col}_cagr'] = cagr.where(years.notna())   # 1 ** nan == 1 in numpy
        prev = out.groupby('iso3')[col].shift(1)
        prev_year = out.groupby('iso3')['year'].shift(1)
        yoy = out[col] / prev.where(prev > 0) - 1.0
        out[f'{col}_yoy'] = yoy.where(prev_year == out['year'] - 1)   # only true neighbours
    return out.sort_index()


def _gdp_threshold(min_gdp_growth):
    return 100.0 * (1.0 + min_gdp_growth) - 1e-9     # tolerance: 100 * 1.1 = 110.00000000000001


def decoupled(gdp_idx, co2_idx, min_gdp_growth=MIN_GDP_GROWTH):
    """Absolute decoupling test on index values (arrays or Series). Missing -> False."""
    gdp_idx = np.asarray(gdp_idx, float)
    co2_idx = np.asarray(co2_idx, float)
    with np.errstate(invalid='ignore'):
        return (gdp_idx >= _gdp_threshold(min_gdp_growth)) & (co2_idx < 100.0)


def add_decoupling_flags(df, min_gdp_growth=MIN_GDP_GROWTH):
    """Add decoupled_terr / decoupled_cons / decoupled_both (needs the _idx columns)."""
    out = df if 'gdp_idx' in df else add_indexed(df)
    out = out.copy()
    out['decoupled_terr'] = decoupled(out['gdp_idx'], out['co2_idx'], min_gdp_growth)
    out['decoupled_cons'] = decoupled(out['gdp_idx'], out['cons_co2_idx'], min_gdp_growth)
    out['decoupled_both'] = out['decoupled_terr'] & out['decoupled_cons']
    return out


def add_metrics(df, min_gdp_growth=MIN_GDP_GROWTH):
    """Everything above in one call. Returns a new table; df is not modified."""
    return add_decoupling_flags(add_growth(add_indexed(df)), min_gdp_growth)


def decoupling_class(gdp_idx, co2_idx, min_gdp_growth=MIN_GDP_GROWTH):
    """'absolute', 'relative', 'none', 'no growth' or 'no data' for one country-year."""
    if not (np.isfinite(gdp_idx) and np.isfinite(co2_idx)):
        return 'no data'
    if gdp_idx < _gdp_threshold(min_gdp_growth):
        return 'no growth'
    if co2_idx < 100.0:
        return 'absolute'
    if co2_idx < gdp_idx:
        return 'relative'
    return 'none'


def decoupling_summary(df, year=2022, min_gdp_growth=MIN_GDP_GROWTH):
    """One row per country for `year`: indices, classes on both bases and a Q1 category.

    Countries without a 1990 GDP or territorial CO2 baseline are left out.
    """
    if 'gdp_idx' not in df:
        df = add_indexed(df)
    rows = df[(df['year'] == year)].dropna(subset=['gdp_idx', 'co2_idx']).copy()
    rows['terr_class'] = [decoupling_class(g, c, min_gdp_growth)
                          for g, c in zip(rows['gdp_idx'], rows['co2_idx'])]
    rows['cons_class'] = [decoupling_class(g, c, min_gdp_growth)
                          for g, c in zip(rows['gdp_idx'], rows['cons_co2_idx'])]
    terr = rows['terr_class'] == 'absolute'
    cons = rows['cons_class'] == 'absolute'
    has_cons = rows['cons_co2_idx'].notna()
    rows['category'] = np.select(
        [~has_cons, terr & cons, terr & ~cons, ~terr & cons],
        [NO_CONS, BOTH, TERR_ONLY, CONS_ONLY], default=NEITHER)
    # gap > 0: the consumption-based index fell less than the territorial one
    rows['basis_gap'] = rows['cons_co2_idx'] - rows['co2_idx']
    cols = ['iso3', 'country', 'continent', 'gdp_idx', 'co2_idx', 'cons_co2_idx',
            'basis_gap', 'terr_class', 'cons_class', 'category']
    rows['category'] = pd.Categorical(rows['category'], CATEGORY_ORDER, ordered=True)
    return rows[cols].sort_values(['category', 'co2_idx']).reset_index(drop=True)
