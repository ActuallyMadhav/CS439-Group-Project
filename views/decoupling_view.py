# View C: decoupling chart, indexed time series (owner: Shivam Rastogi)
#
# Small multiples, one panel per selected country (up to MAX_PANELS), each showing
# GDP, territorial CO2 and consumption-based CO2 indexed to 1990 = 100 on a shared
# log y-axis (equal ratios look equal: 50 and 200 are the same distance from 100).
#
# Driven by the shared SelectionModel:
#   selected  -> which countries get a panel (the most populous MAX_PANELS)
#   basis     -> the active basis is drawn bold and drives the shading; the other
#                basis stays visible but faded, because the gap between the two
#                CO2 lines is the point of the view
#   year      -> a vertical marker and dots follow the year slider / play
#   continent -> only used when nothing is selected (shows that continent's
#                largest economies instead of the default examples)
#
# Shading: years where the country is absolutely decoupled on the active basis,
# i.e. GDP >= 1990 * (1 + MIN_GDP_GROWTH) while CO2 < 1990 (see metrics.py).
#
# Patterns reused from the team code / homework: BaseView contract and QWidget panel
# holding self.figure + self.canvas (view B, HW2); artists rebuilt only when the set
# of panels changes, cheap set_data updates on every year step (HW3).
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from PyQt5 import QtWidgets

from metrics import BASIS_COL, MIN_GDP_GROWTH, add_metrics
from selection import BaseView, YEAR_MAX, YEAR_MIN

MAX_PANELS = 4
DEFAULT_COUNTRIES = ('GBR', 'USA', 'DEU', 'CHN')   # shown when nothing is selected

# Okabe-Ito colors (safe for color-vision deficiencies), same family as view B
SERIES = {  # key -> (label, color)
    'gdp': ('GDP', '#222222'),
    'co2': ('Territorial CO₂', '#D55E00'),
    'cons_co2': ('Consumption-based CO₂', '#0072B2'),
}
SHADE_COLOR = '#009E73'
SHADE_ALPHA = 0.16
INACTIVE_ALPHA = 0.45
Y_TICKS = [12.5, 25, 50, 100, 200, 400, 800, 1600]
BASIS_LABEL = {'territorial': 'territorial', 'consumption': 'consumption-based'}


def fmt_pct_change(idx):
    if not np.isfinite(idx):
        return 'n/a'
    return f'{idx - 100:+.0f}%'


def runs(mask):
    """(start, end) index pairs of consecutive True values in a boolean array."""
    mask = np.asarray(mask, bool)
    edges = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1))


class DecouplingPanel(QtWidgets.QWidget, BaseView):
    """Team interface: draw(df) once, update_view(state) on every change."""

    def __init__(self, model, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        BaseView.__init__(self, model)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(11, 7))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=1)
        self.years = np.arange(YEAR_MIN, YEAR_MAX + 1)
        self.panels = []          # one dict per drawn country panel
        self._layout_key = None   # (countries, basis) the panels were built for
        self._hover = None        # (panel index, year) currently shown in the tooltip
        self.ready = False
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.canvas.mpl_connect('figure_leave_event', lambda e: self._show_tooltip(None, None))

    # ------------------------------------------------------------------ draw
    def draw(self, df):
        """Precompute one (countries x years) array per series, then build the panels."""
        if 'gdp_idx' not in df:
            df = add_metrics(df)
        order = df.drop_duplicates('iso3')['iso3'].to_numpy()

        def grid(col):
            return (df.pivot_table(index='iso3', columns='year', values=col, aggfunc='first')
                    .reindex(index=order, columns=self.years).to_numpy(float))

        meta = df.drop_duplicates('iso3').set_index('iso3').loc[order]
        self.iso = order
        self.row = {c: i for i, c in enumerate(order)}
        self.names = meta['country'].to_numpy()
        self.cont = meta['continent'].to_numpy()
        self.idx = {k: grid(f'{k}_idx') for k in SERIES}
        self.flags = {'territorial': grid('decoupled_terr') > 0,
                      'consumption': grid('decoupled_cons') > 0}
        self.raw = {c: grid(c) for c in ('gdp_pc', 'co2_pc', 'cons_co2_pc', 'population')}
        self.has_base = np.isfinite(self.idx['gdp'][:, 0]) & np.isfinite(self.idx['co2'][:, 0])
        self.ready = True
        self._layout_key = None
        self.update_view(self.model.state)

    # ------------------------------------------------------- which countries
    def choose_countries(self, state):
        """Rows to draw, plus notes explaining anything that was left out."""
        notes = []
        j = state.year - YEAR_MIN
        pop = np.nan_to_num(self.raw['population'][:, j], nan=0.0)

        if state.selected:
            known = [self.row[c] for c in state.selected if c in self.row]
            missing = [self.names[i] for i in known if not self.has_base[i]]
            rows = [i for i in known if self.has_base[i]]
            if missing:
                notes.append('No 1990 GDP/CO₂ baseline: ' + ', '.join(sorted(missing)))
            rows.sort(key=lambda i: -pop[i])
            if len(rows) > MAX_PANELS:
                notes.append(f'+{len(rows) - MAX_PANELS} more selected '
                             f'(showing the {MAX_PANELS} most populous)')
            return rows[:MAX_PANELS], notes, False

        if state.continent is not None:
            gdp = np.nan_to_num(self.raw['gdp_pc'][:, -1] * self.raw['population'][:, -1], nan=0.0)
            cand = [i for i in np.argsort(-gdp) if self.cont[i] == state.continent and self.has_base[i]]
            notes.append(f'Nothing selected: largest economies in {state.continent}')
            return cand[:MAX_PANELS], notes, True

        notes.append('Nothing selected: example countries. Click or brush countries '
                     'in the map, bubble chart or scatter to compare them here.')
        return [self.row[c] for c in DEFAULT_COUNTRIES if c in self.row], notes, True

    # ---------------------------------------------------------------- update
    def update_view(self, state):
        if not self.ready:
            return  # draw(df) has not run yet
        rows, notes, is_default = self.choose_countries(state)
        key = (tuple(rows), state.basis)
        if key != self._layout_key:
            self._build_panels(rows, state.basis, notes, is_default)
            self._layout_key = key
        else:
            self.note_text.set_text('\n'.join(notes))
        self._update_year(state)
        self.canvas.draw_idle()

    def _build_panels(self, rows, basis, notes, is_default):
        """Rebuild the small multiples (only when the countries or the basis change)."""
        self.figure.clear()
        self.panels = []
        self._hover = None
        active = BASIS_COL[basis]
        n = len(rows)
        ncols = 1 if n <= 1 else 2
        nrows = max(1, int(np.ceil(n / ncols)))
        self.figure.subplots_adjust(left=0.08, right=0.97, top=0.80, bottom=0.12,
                                    wspace=0.08, hspace=0.32)

        self.figure.suptitle('Did growth decouple from emissions? (1990 = 100)',
                             weight='bold', fontsize=13, y=0.975)
        self._legend(basis)
        self.note_text = self.figure.text(0.08, 0.015, '\n'.join(notes), fontsize=8.5,
                                          color='#555555', va='bottom')
        if n == 0:
            ax = self.figure.add_subplot(111)
            ax.axis('off')
            ax.text(0.5, 0.5, 'No selected country has a 1990 baseline to index against.',
                    ha='center', va='center', fontsize=11, color='#555555')
            return

        lo, hi = self._y_limits(rows)
        axes = self.figure.subplots(nrows, ncols, sharex=True, sharey=True, squeeze=False).ravel()
        for ax in axes[n:]:
            ax.set_visible(False)

        for k, (ax, i) in enumerate(zip(axes, rows)):
            ax.set_yscale('log')
            ax.set_ylim(lo, hi)
            ax.set_xlim(YEAR_MIN - 0.5, YEAR_MAX + 0.5)
            ax.yaxis.set_major_locator(FixedLocator([t for t in Y_TICKS if lo <= t <= hi]))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f'{v:g}'))
            ax.yaxis.set_minor_locator(NullLocator())
            ax.xaxis.set_major_locator(FixedLocator([1990, 1995, 2000, 2005, 2010, 2015, 2020]))
            ax.grid(True, color='#e6e6e6', linewidth=0.8)
            ax.set_axisbelow(True)
            ax.axhline(100, color='#888888', linewidth=1.0, linestyle=(0, (4, 3)), zorder=1)

            # shading: years decoupled on the active basis
            for s, e in runs(self.flags[basis][i]):
                ax.axvspan(self.years[s] - 0.5, self.years[e] + 0.5, color=SHADE_COLOR,
                           alpha=SHADE_ALPHA, linewidth=0, zorder=0)

            dots = {}
            for key, (label, color) in SERIES.items():
                is_active = key in ('gdp', active)
                ax.plot(self.years, self.idx[key][i], color=color,
                        linewidth=2.4 if is_active else 1.3,
                        linestyle='-' if is_active else (0, (5, 2)),
                        alpha=1.0 if is_active else INACTIVE_ALPHA, zorder=3 if is_active else 2)
                dots[key], = ax.plot([], [], 'o', color=color, markersize=6 if is_active else 4,
                                     alpha=1.0 if is_active else INACTIVE_ALPHA,
                                     markeredgecolor='white', zorder=5)

            ax.set_title(f'{self.names[i]}', loc='left', weight='bold', fontsize=11)
            if not np.isfinite(self.idx['cons_co2'][i]).any():
                ax.text(0.98, 0.04, 'no consumption-based estimate', transform=ax.transAxes,
                        ha='right', va='bottom', fontsize=8, color='#777777', style='italic')
            year_line = ax.axvline(YEAR_MAX, color='#444444', linewidth=0.9,
                                   linestyle=':', zorder=4)
            change = ax.text(0.02, 0.97, '', transform=ax.transAxes, ha='left', va='top',
                             fontsize=8.5, family='monospace', zorder=6,
                             bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='none', alpha=0.85))
            tip = ax.annotate('', xy=(0, 0), xytext=(12, 12), textcoords='offset points',
                              fontsize=8, family='monospace', zorder=10, annotation_clip=False,
                              bbox=dict(boxstyle='round', fc='white', ec='black', alpha=0.92),
                              visible=False)
            if k % ncols == 0:
                ax.set_ylabel('Index (1990 = 100, log)')
            self.panels.append(dict(ax=ax, row=i, dots=dots, year_line=year_line,
                                    change=change, tip=tip))

    def _legend(self, basis):
        active = BASIS_COL[basis]
        handles, labels = [], []
        for key, (label, color) in SERIES.items():
            is_active = key in ('gdp', active)
            handles.append(Line2D([], [], color=color, linewidth=2.4 if is_active else 1.3,
                                  linestyle='-' if is_active else (0, (5, 2)),
                                  alpha=1.0 if is_active else INACTIVE_ALPHA))
            labels.append(label + ('' if is_active else ' (other basis)'))
        handles.append(Patch(color=SHADE_COLOR, alpha=SHADE_ALPHA * 2))
        labels.append(f'Decoupled: GDP ≥ +{MIN_GDP_GROWTH:.0%} and {BASIS_LABEL[basis]} '
                      f'CO₂ below 1990')
        # two columns, so the legend also fits when the view is half the window wide
        self.figure.legend(handles, labels, loc='upper center', ncol=2, frameon=False,
                           fontsize=9, bbox_to_anchor=(0.5, 0.945))

    def _y_limits(self, rows):
        vals = np.concatenate([self.idx[k][rows].ravel() for k in SERIES])
        vals = vals[np.isfinite(vals) & (vals > 0)]
        if len(vals) == 0:
            return 50, 200
        return min(70.0, vals.min()) / 1.12, max(150.0, vals.max()) * 1.12

    def _update_year(self, state):
        """Cheap per-frame update: year marker, dots and the 'since 1990' box."""
        j = state.year - YEAR_MIN
        active = BASIS_COL[state.basis]
        for p in self.panels:
            i = p['row']
            p['year_line'].set_xdata([state.year, state.year])
            for key, dot in p['dots'].items():
                v = self.idx[key][i, j]
                dot.set_data([state.year] if np.isfinite(v) else [],
                             [v] if np.isfinite(v) else [])
            g, c = self.idx['gdp'][i, j], self.idx[active][i, j]
            status = 'decoupled' if self.flags[state.basis][i, j] else 'not decoupled'
            p['change'].set_text(f'1990→{state.year}  GDP {fmt_pct_change(g)}  '
                                 f'CO₂ {fmt_pct_change(c)}  ({status})')

    # ----------------------------------------------------------- interaction
    def tooltip_text(self, i, year):
        j = year - YEAR_MIN
        r = self.raw

        def line(label, key, raw_key, unit):
            v = self.idx[key][i, j]
            if not np.isfinite(v):
                return f'{label:<13}no estimate'
            return f'{label:<13}{v:5.0f}  ({unit.format(r[raw_key][i, j])})'

        flags = [b for b in ('territorial', 'consumption') if self.flags[b][i, j]]
        return '\n'.join([
            f'{self.names[i]} ({year})',
            line('GDP', 'gdp', 'gdp_pc', '${:,.0f}/person'),
            line('Territorial', 'co2', 'co2_pc', '{:.1f} t/person'),
            line('Consumption', 'cons_co2', 'cons_co2_pc', '{:.1f} t/person'),
            f'{"Population":<13}{r["population"][i, j] / 1e6:,.1f} million',
            'Decoupled:   ' + (', '.join(flags) if flags else 'no'),
        ])

    def _on_motion(self, event):
        k = next((n for n, p in enumerate(self.panels) if p['ax'] is event.inaxes), None)
        if k is None or event.xdata is None:
            self._show_tooltip(None, None)
            return
        year = int(np.clip(round(event.xdata), YEAR_MIN, YEAR_MAX))
        self._show_tooltip(k, year)

    def _show_tooltip(self, k, year):
        if (k, year) == (self._hover or (None, None)):
            return
        if self._hover is not None and self._hover[0] < len(self.panels):
            self.panels[self._hover[0]]['tip'].set_visible(False)
        self._hover = None if k is None else (k, year)
        if k is not None:
            p = self.panels[k]
            i, j = p['row'], year - YEAR_MIN
            y = self.idx['gdp'][i, j]
            if not np.isfinite(y):
                y = 100.0
            ax = p['ax']
            px, py = ax.transData.transform((year, y))
            right = px > ax.bbox.x0 + ax.bbox.width * 0.5
            top = py > ax.bbox.y0 + ax.bbox.height * 0.5
            tip = p['tip']
            tip.xy = (year, y)
            tip.set_text(self.tooltip_text(i, year))
            tip.set_position((-12 if right else 12, -12 if top else 12))
            tip.set_horizontalalignment('right' if right else 'left')
            tip.set_verticalalignment('top' if top else 'bottom')
            tip.set_visible(True)
        self.canvas.draw_idle()
