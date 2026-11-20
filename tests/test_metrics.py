"""Tests for the derived metrics (owner: Shivam Rastogi).

Run (no GUI needed):
    python tests/test_metrics.py <owid-co2-data.csv> <ne_50m.geojson>
or with pytest (data paths default to data/raw/):
    pytest tests/test_metrics.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd

import metrics
from metrics import add_metrics, decoupling_class, decoupling_summary

RAW = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')


def _toy():
    """Two made-up countries: A decouples, B has no 1990 data."""
    return pd.DataFrame({
        'iso3': ['AAA'] * 3 + ['BBB'] * 2,
        'country': ['A'] * 3 + ['B'] * 2,
        'continent': ['Europe'] * 5,
        'year': [1990, 1991, 1992, 1991, 1992],
        'population': [10.0] * 5,
        'gdp': [100.0, 110.0, 121.0, 50.0, 60.0],
        'gdp_pc': [10.0, 11.0, 12.1, 5.0, 6.0],
        'co2': [10.0, 9.0, 8.0, 1.0, 2.0],
        'co2_pc': [1.0, 0.9, 0.8, 0.1, 0.2],
        'cons_co2': [10.0, 11.0, 12.0, np.nan, np.nan],
        'cons_co2_pc': [1.0, 1.1, 1.2, np.nan, np.nan],
    })


def test_toy():
    df = add_metrics(_toy())
    a = df[df.iso3 == 'AAA'].set_index('year')
    b = df[df.iso3 == 'BBB'].set_index('year')

    # indexing: 100 in 1990, ratios afterwards, NaN without a 1990 baseline
    for col in metrics.INDEX_COLS:
        assert a.loc[1990, f'{col}_idx'] == 100.0
        assert b[f'{col}_idx'].isna().all()
    assert np.isclose(a.loc[1992, 'gdp_idx'], 121.0)
    assert np.isclose(a.loc[1992, 'co2_idx'], 80.0)

    # growth: 21 % over two years = 10 %/year; 1990 itself has no CAGR
    assert np.isnan(a.loc[1990, 'gdp_cagr'])
    assert np.isclose(a.loc[1992, 'gdp_cagr'], 0.10)
    assert np.isclose(a.loc[1992, 'gdp_yoy'], 0.10)
    assert np.isnan(b.loc[1991, 'gdp_yoy'])           # no 1990 row to compare with
    assert np.isclose(b.loc[1992, 'gdp_yoy'], 0.20)

    # flags: GDP +10 % and CO2 down -> decoupled territorially, not on consumption
    assert not a.loc[1990, 'decoupled_terr']           # no growth yet
    assert a.loc[1991, 'decoupled_terr'] and a.loc[1992, 'decoupled_terr']
    assert not a['decoupled_cons'].any()
    assert not a['decoupled_both'].any()
    assert not b[['decoupled_terr', 'decoupled_cons']].any().any()   # missing -> False

    # input is not modified
    assert 'gdp_idx' not in _toy().columns


def test_classes():
    assert decoupling_class(150, 80) == 'absolute'
    assert decoupling_class(150, 120) == 'relative'
    assert decoupling_class(150, 160) == 'none'
    assert decoupling_class(105, 50) == 'no growth'
    assert decoupling_class(np.nan, 50) == 'no data'


def test_real(co2_file=None, map_file=None):
    from data_minimal import load_table
    co2_file = co2_file or os.path.join(RAW, 'owid-co2-data.csv')
    map_file = map_file or os.path.join(RAW, 'ne_50m_admin_0_countries.geojson')
    df = add_metrics(load_table(co2_file, map_file))

    base = df[df.year == 1990]
    assert np.allclose(base['gdp_idx'].dropna(), 100.0)
    assert np.allclose(base['co2_idx'].dropna(), 100.0)
    assert len(df) == len(load_table(co2_file, map_file))   # no rows lost or added

    summary = decoupling_summary(df, 2022).set_index('iso3')
    # textbook cases: the UK cut on both bases, China grew emissions with GDP
    assert summary.loc['GBR', 'terr_class'] == 'absolute'
    assert summary.loc['GBR', 'category'] == metrics.BOTH
    assert summary.loc['CHN', 'terr_class'] == 'relative'
    assert summary.loc['CHN', 'category'] == metrics.NEITHER
    # the UK's consumption-based cut is smaller than its territorial cut
    assert summary.loc['GBR', 'basis_gap'] > 0
    counts = summary['category'].value_counts()
    print('real data: 2022 categories\n' + counts.to_string())


if __name__ == '__main__':
    test_toy()
    test_classes()
    test_real(*sys.argv[1:3])
    print('ALL METRICS TESTS PASSED')
