# View D: outsourced emissions, territorial vs consumption scatter (owner: Tanisha Phadke)
#
# x = territorial CO2 per person, y = consumption-based CO2 per person, both log,
# with the y = x diagonal. A country above the diagonal consumes more CO2 than it
# emits at home (a net importer of emissions: part of its footprint is emitted
# abroad); below it, part of its emissions serve other countries' consumption.
#
# Driven by the shared SelectionModel:
#   year      -> moves the points (play = stepping the year)
#   continent -> countries outside it are faded and cannot be hovered
#   selected  -> selected countries keep their color and get a name label,
#                the rest turn grey (HW2)
#   basis     -> not used: this view always shows both bases, that is its point
#
# Built from our homework code and the team's view B:
#   HW1  continent -> color dictionary (shared in tooltip.py)
#   HW2  QWidget panel holding figure + canvas, grey EXCLUDED_COLOR for unselected
#   HW3  build artists once and update them with set_offsets / set_facecolors,
#        blit-based hover tooltip (tooltip.HoverTooltip, shared by all views)
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from PyQt5 import QtWidgets

from selection import BaseView, CONTINENTS, YEAR_MIN, YEAR_MAX
from tooltip import (CONTINENT_COLORS, EXCLUDED_COLOR, SELECTED_LW, UNSELECTED_LW,
                     HoverTooltip, country_text, rgb)

LIM = (0.02, 100)          # tonnes CO2 per person, same range as view B's y axis
CAP = LIM[1] * 0.85        # off-scale values (Kuwait 1991 oil fires) are pinned here
TICKS = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50]
POINT_AREA = 55.0          # points^2; size carries no data here (view B shows population)
IMPORTER_TINT = '#0072B2'
DIAGONAL_COLOR = '#444444'


def fmt_tonnes(v, _pos=None):
    return f'{v:g}'


class OutsourcingPanel(QtWidgets.QWidget, BaseView):
    """Team interface: draw(df) once, update_view(state) on every change."""

    def __init__(self, model, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        BaseView.__init__(self, model)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(9, 7))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=1)
        self.ax = None
        self.labels = []

    # ------------------------------------------------------------------ draw
    def draw(self, df):
        """Precompute one (countries x years) array per variable, build artists once."""
        df = df[df['continent'].isin(CONTINENTS)]          # drops World and unmapped codes
        codes = df.dropna(subset=['co2_pc', 'cons_co2_pc'])['iso3'].unique()
        df = df[df['iso3'].isin(codes)]
        order = np.sort(codes)
        years = np.arange(YEAR_MIN, YEAR_MAX + 1)

        def grid(col):
            return (df.pivot_table(index='iso3', columns='year', values=col, aggfunc='first')
                    .reindex(index=order, columns=years).to_numpy(float))

        meta = df.drop_duplicates('iso3').set_index('iso3').loc[order]
        self.iso = np.array(order)
        self.names = meta['country'].to_numpy()
        self.cont = meta['continent'].to_numpy()
        self.T, self.C = grid('co2_pc'), grid('cons_co2_pc')
        self.G, self.P = grid('gdp_pc'), grid('population')
        self.colors = np.array([[*rgb(CONTINENT_COLORS[c]), 1.0] for c in self.cont])

        self._build_plot()
        self.update_view(self.model.state)

    def _build_plot(self):
        self.ax = ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.10, right=0.78, top=0.92, bottom=0.10)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlim(*LIM)
        ax.set_ylim(*LIM)
        ax.set_box_aspect(1)      # same limits on both axes -> the diagonal is at 45 degrees
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(FixedLocator(TICKS))
            axis.set_major_formatter(FuncFormatter(fmt_tonnes))
            axis.set_minor_locator(NullLocator())
        ax.grid(True, color='#e6e6e6', linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlabel('Territorial CO₂ per person (tonnes, log scale)')
        ax.set_ylabel('Consumption-based CO₂ per person (tonnes, log scale)')

        # the diagonal and the two regions it separates (proposal, sketch 2)
        line = np.array(LIM)
        ax.fill_between(line, line, LIM[1], color=IMPORTER_TINT, alpha=0.06, zorder=0, linewidth=0)
        ax.plot(line, line, linestyle='--', color=DIAGONAL_COLOR, linewidth=1.2, zorder=1)
        ax.text(0.03, 0.97, 'Net importers of emissions\nconsume more CO₂ than they emit',
                transform=ax.transAxes, ha='left', va='top', fontsize=9.5, color=IMPORTER_TINT,
                weight='bold')
        ax.text(0.97, 0.03, 'Net exporters of emissions\npart of their CO₂ serves others',
                transform=ax.transAxes, ha='right', va='bottom', fontsize=9.5, color='#8a4a00',
                weight='bold')
        ax.text(0.80, 0.86, 'consumption = territorial', transform=ax.transAxes, rotation=45,
                ha='center', va='center', fontsize=8, color=DIAGONAL_COLOR)

        self.year_text = ax.text(0.5, 0.5, '', transform=ax.transAxes, ha='center', va='center',
                                 fontsize=90, color='black', alpha=0.06, weight='bold', zorder=0)
        self.note_text = self.figure.text(0.79, 0.10, '', fontsize=8.5, color='#555555', va='bottom')

        n = len(self.iso)
        self.points = ax.scatter(np.full(n, np.nan), np.full(n, np.nan), s=np.full(n, POINT_AREA),
                                 edgecolors='black', linewidths=UNSELECTED_LW, zorder=2)

        handles = [plt.Line2D([], [], linestyle='none', marker='o', markersize=8,
                              markerfacecolor=CONTINENT_COLORS[c], markeredgecolor='black')
                   for c in CONTINENTS]
        ax.legend(handles, CONTINENTS, title='Continent', title_fontproperties={'weight': 'bold'},
                  loc='upper left', bbox_to_anchor=(1.02, 1.0))

        self.tooltip = HoverTooltip(self.figure, ax, node_text=self._tooltip_text)

    # ---------------------------------------------------------------- update
    def update_view(self, state):
        if self.ax is None:
            return  # draw(df) has not run yet
        j = state.year - YEAR_MIN
        x, y = self.T[:, j], self.C[:, j]
        valid = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
        capped = valid & ((x > CAP) | (y > CAP))
        x_plot, y_plot = np.minimum(x, CAP), np.minimum(y, CAP)
        in_cont = np.ones(len(self.iso), bool) if state.continent is None else (self.cont == state.continent)
        selected = np.isin(self.iso, list(state.selected))
        pickable = valid & in_cont

        # same highlight rules as view B (HW2)
        face = self.colors.copy()
        face[:, 3] = 0.8
        grey = (~selected if selected.any() else np.zeros(len(self.iso), bool)) | ~in_cont
        face[grey] = [*EXCLUDED_COLOR, 0.4]
        face[~in_cont, 3] = 0.15
        face[selected & in_cont, 3] = 1.0

        offsets = np.column_stack([np.where(valid, x_plot, np.nan), np.where(valid, y_plot, np.nan)])
        # selected points on top: one collection is drawn in order, so sort it
        order = np.argsort(selected, kind='stable')
        self.points.set_offsets(offsets[order])
        self.points.set_facecolors(face[order])
        self.points.set_edgecolors(np.where(grey[order, None], [[0, 0, 0, 0]], [[0, 0, 0, 1]]))
        self.points.set_linewidths(np.where(selected[order], SELECTED_LW, UNSELECTED_LW))

        self._cur = dict(j=j, x=x, y=y, x_plot=x_plot, y_plot=y_plot, valid=valid,
                         capped=capped, pickable=pickable, state=state)
        self._draw_labels(selected & valid)
        self._update_text(state, valid, capped)

        ids = np.flatnonzero(pickable)
        self.tooltip.set_data(np.column_stack([x_plot[ids], y_plot[ids]]),
                              np.full(len(ids), POINT_AREA), ids)
        self.canvas.draw_idle()

    def _draw_labels(self, chosen):
        for t in self.labels:
            t.remove()
        self.labels = []
        c = self._cur
        chosen = np.flatnonzero(chosen)
        chosen = chosen[np.argsort(c['y_plot'][chosen])]   # alternate above/below by height (view B)
        for rank, i in enumerate(chosen):
            offset = (7, 7) if rank % 2 == 0 else (7, -13)
            self.labels.append(self.ax.annotate(
                self.names[i], (c['x_plot'][i], c['y_plot'][i]), xytext=offset,
                textcoords='offset points', fontsize=9, weight='bold', zorder=4))

    def _update_text(self, state, valid, capped):
        j = state.year - YEAR_MIN
        self.year_text.set_text(str(state.year))
        self.ax.set_title(f'Outsourced emissions, {state.year}: territorial vs consumption CO₂',
                          weight='bold')
        above = valid & (self.C[:, j] > self.T[:, j])
        notes = [f'{int(valid.sum())} countries with',
                 'both measures:',
                 f'  {int(above.sum())} net importers',
                 f'  {int((valid & ~above).sum())} net exporters']
        for i in np.flatnonzero(capped):
            notes.append(f'\n{self.names[i]}: {self.T[i, j]:.0f} t/person\n'
                         f'territorial, off scale\n(drawn at the edge)')
        notes.append('\nHover a point for details')
        self.note_text.set_text('\n'.join(notes))

    # ----------------------------------------------------------- interaction
    def _tooltip_text(self, i):
        c = self._cur
        j = c['j']
        t, k = self.T[i, j], self.C[i, j]
        net = k - t
        kind = 'importer' if net > 0 else 'exporter'
        extra = [('Net imported', f'{net:+.1f} t/person ({100 * net / t:+.0f}%, net {kind})')]
        if c['capped'][i]:
            extra.append(('Off scale', 'drawn at the edge'))
        return country_text(self.names[i], c['state'].year, self.cont[i], t, k,
                            self.G[i, j], self.P[i, j], extra)
