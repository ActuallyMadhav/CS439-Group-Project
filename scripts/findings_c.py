"""Findings for questions 1 and 3 (owner: Shivam Rastogi).

    python scripts/findings_c.py -i data/raw/owid-co2-data.csv \
        -m data/raw/ne_50m_admin_0_countries.geojson -o docs/view_c

Q1  Which countries grew richer while cutting emissions, and does that still hold
    on a consumption basis?          -> q1_decoupling_2022.csv, findings.md
Q3  As countries get richer, do emissions per person keep rising, level off or
    fall?                            -> q3_wealth_curve.csv, q3_wealth_curve.png, findings.md
Everything is computed from the shared table + metrics.py, so the numbers can be
regenerated whenever the data pipeline changes.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

import metrics
from data import WORLD, load_table

YEAR = 2022
COMPARE_YEAR = 1990
# GDP per person bins (international $, 2011 prices), roughly doubling each step
GDP_BINS = [0, 1_000, 2_000, 4_000, 8_000, 16_000, 32_000, 64_000, np.inf]
MIN_PER_BIN = 3        # medians of fewer countries are not reported


def bin_label(lo, hi):
    def k(v):
        return f'${v / 1000:g}k' if v >= 1000 else f'${v:g}'
    if hi == np.inf:
        return f'> {k(lo)}'
    if lo == 0:
        return f'< {k(hi)}'
    return f'{k(lo)}-{k(hi)}'


# ------------------------------------------------------------------ Q1
def q1(df):
    s = metrics.decoupling_summary(df, YEAR)
    s['gdp_change_%'] = (s['gdp_idx'] - 100).round(0)
    s['terr_co2_change_%'] = (s['co2_idx'] - 100).round(0)
    s['cons_co2_change_%'] = (s['cons_co2_idx'] - 100).round(0)
    s['basis_gap_pts'] = s['basis_gap'].round(0)
    return s[['iso3', 'country', 'continent', 'category', 'gdp_change_%',
              'terr_co2_change_%', 'cons_co2_change_%', 'basis_gap_pts',
              'terr_class', 'cons_class']]


# ------------------------------------------------------------------ Q3
def wealth_curve(df, year):
    d = df[df['year'] == year].dropna(subset=['gdp_pc'])
    d = d.assign(bin=pd.cut(d['gdp_pc'], GDP_BINS, right=False))
    rows = []
    for interval, g in d.groupby('bin', observed=True):
        for basis, col in (('territorial', 'co2_pc'), ('consumption', 'cons_co2_pc')):
            v = g[col].dropna()
            rows.append(dict(year=year, gdp_bin=bin_label(interval.left, interval.right),
                             gdp_mid=np.sqrt(max(interval.left, 500) * min(interval.right, 128_000)),
                             basis=basis, n=len(v),
                             median_t_per_person=v.median() if len(v) >= MIN_PER_BIN else np.nan))
    return pd.DataFrame(rows)


def within_country_trend(df):
    """For each rich country (> $32k in 2022): did CO2 per person peak and fall?"""
    rows = []
    rich = df[(df['year'] == YEAR) & (df['gdp_pc'] > 32_000)]['iso3']
    for iso in rich:
        c = df[df['iso3'] == iso].set_index('year')
        for basis, col in (('territorial', 'co2_pc'), ('consumption', 'cons_co2_pc')):
            s = c[col].dropna()
            if len(s) < 10:
                continue
            peak = s.idxmax()
            rows.append(dict(iso3=iso, country=c['country'].iloc[0], basis=basis,
                             peak_year=int(peak), peak=s.max(), latest=s.iloc[-1],
                             change_since_peak_pct=100 * (s.iloc[-1] / s.max() - 1)))
    return pd.DataFrame(rows)


def plot_curve(curve, path):
    fig = Figure(figsize=(9, 5.5))
    ax = fig.add_subplot(111)
    styles = {('territorial', COMPARE_YEAR): ('#D55E00', ':', 'o'),
              ('territorial', YEAR): ('#D55E00', '-', 'o'),
              ('consumption', COMPARE_YEAR): ('#0072B2', ':', 's'),
              ('consumption', YEAR): ('#0072B2', '-', 's')}
    for (basis, year), (color, ls, marker) in styles.items():
        c = curve[(curve.basis == basis) & (curve.year == year)].dropna(subset=['median_t_per_person'])
        if len(c):
            ax.plot(c['gdp_mid'], c['median_t_per_person'], color=color, linestyle=ls,
                    marker=marker, linewidth=2 if year == YEAR else 1.3,
                    label=f'{basis.capitalize()}, {year}')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.xaxis.set_major_locator(FixedLocator([1000, 2000, 4000, 8000, 16000, 32000, 64000]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f'${v / 1000:g}k'))
    ax.yaxis.set_major_locator(FixedLocator([0.1, 0.2, 0.5, 1, 2, 5, 10, 20]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f'{v:g}'))
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_minor_locator(NullLocator())
    ax.grid(True, color='#e6e6e6')
    ax.set_xlabel('GDP per person (international $, 2011 prices, log scale)')
    ax.set_ylabel('Median CO₂ per person (tonnes, log scale)')
    ax.set_title('Q3: emissions per person across the wealth ladder', weight='bold')
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


# ------------------------------------------------------------------ report
def md_table(df):
    cols = list(df.columns)
    lines = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        lines.append('| ' + ' | '.join('' if pd.isna(v) else
                                       (f'{v:.1f}' if isinstance(v, float) else str(v))
                                       for v in r) + ' |')
    return '\n'.join(lines)


def write_findings(out, s1, curve, trend):
    counts = s1['category'].value_counts().reindex(metrics.CATEGORY_ORDER).fillna(0).astype(int)
    terr_only = s1[s1.category == metrics.TERR_ONLY]
    both = s1[s1.category == metrics.BOTH]
    with_cons = s1[s1.category != metrics.NO_CONS]
    terr_dec = with_cons[with_cons.terr_class == 'absolute']

    pivot = (curve.pivot_table(index=['gdp_bin', 'gdp_mid'], columns=['basis', 'year'],
                               values='median_t_per_person')
             .sort_index(level='gdp_mid').droplevel('gdp_mid').round(2))
    pivot.columns = [f'{b} {y}' for b, y in pivot.columns]
    pivot = pivot.reset_index()
    n_by_bin = curve[(curve.year == YEAR) & (curve.basis == 'territorial')].set_index('gdp_bin')['n']
    pivot.insert(1, f'countries {YEAR}', pivot['gdp_bin'].map(n_by_bin))

    t = trend[trend.basis == 'consumption']
    fell = t[(t.change_since_peak_pct < -10) & (t.peak_year < YEAR - 5)]
    tt = trend[trend.basis == 'territorial']
    fell_t = tt[(tt.change_since_peak_pct < -10) & (tt.peak_year < YEAR - 5)]

    text = f"""# View C findings: questions 1 and 3

Generated by `scripts/findings_c.py` from the shared table and `metrics.py`.
Decoupling rule: GDP at least {metrics.MIN_GDP_GROWTH:.0%} above 1990 **and** CO₂ below its
1990 level (absolute decoupling, totals, {COMPARE_YEAR}→{YEAR}).

## Q1: Who grew richer while cutting emissions, and does it hold on a consumption basis?

| Category ({YEAR}) | Countries |
|---|---|
""" + '\n'.join(f'| {k} | {v} |' for k, v in counts.items()) + f"""

* Of the {len(with_cons)} countries with both measures, **{len(terr_dec)}** decoupled on the
  official (territorial) basis, but only **{len(both)}** still qualify on a consumption basis.
* **{len(terr_only)} countries' cuts disappear on a consumption basis** (decoupled territorially,
  not on consumption): {', '.join(terr_only['country'])}.
* On median, the consumption-based index of territorially-decoupled countries is
  **{terr_dec['basis_gap_pts'].median():.0f} index points** higher than the territorial one,
  i.e. part of their reported cut was moved abroad.

### Decoupled on both bases (defensible list)
{md_table(both[['country', 'continent', 'gdp_change_%', 'terr_co2_change_%', 'cons_co2_change_%']])}

### Territorial only (cut partly moved abroad)
{md_table(terr_only[['country', 'continent', 'gdp_change_%', 'terr_co2_change_%', 'cons_co2_change_%']])}

Full table: `q1_decoupling_{YEAR}.csv`.

## Q3: As countries get richer, do emissions per person keep rising, level off or fall?

Median CO₂ per person (tonnes) by GDP-per-person band (bands with fewer than
{MIN_PER_BIN} countries are left blank):

{md_table(pivot)}

![Wealth curve](q3_wealth_curve.png)

Within rich countries (GDP > $32k per person in {YEAR}):
* **{len(fell_t)} of {len(tt)}** have territorial CO₂ per person more than 10 % below a peak
  reached before {YEAR - 5}.
* On a consumption basis **{len(fell)} of {len(t)}** do.
* Median peak year: territorial **{tt.peak_year.median():.0f}**, consumption
  **{t.peak_year.median():.0f}**.

Full tables: `q3_wealth_curve.csv`, `q3_rich_country_peaks.csv`.
"""
    with open(os.path.join(out, 'findings.md'), 'w', encoding='utf-8') as f:
        f.write(text)


def main():
    p = argparse.ArgumentParser(description='Findings for questions 1 and 3 (view C)')
    p.add_argument('-i', '--input', required=True, help='owid-co2-data.csv')
    p.add_argument('-m', '--map', dest='map_file', required=True, help='world map (GeoJSON)')
    p.add_argument('-o', '--out', default='docs/view_c', help='output folder')
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)

    df = load_table(args.input, args.map_file)
    df = metrics.add_metrics(df[df['iso3'] != WORLD])   # countries only, not the World row
    s1 = q1(df)
    s1.to_csv(os.path.join(args.out, f'q1_decoupling_{YEAR}.csv'), index=False)

    curve = pd.concat([wealth_curve(df, COMPARE_YEAR), wealth_curve(df, YEAR)])
    curve.to_csv(os.path.join(args.out, 'q3_wealth_curve.csv'), index=False)
    plot_curve(curve, os.path.join(args.out, 'q3_wealth_curve.png'))
    trend = within_country_trend(df)
    trend.round(2).to_csv(os.path.join(args.out, 'q3_rich_country_peaks.csv'), index=False)

    write_findings(args.out, s1, curve, trend)
    print(f'wrote findings to {args.out}/')


if __name__ == '__main__':
    main()
