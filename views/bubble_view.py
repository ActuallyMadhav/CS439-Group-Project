# View B: wealth vs emissions bubble chart (owner: Madhav Anantharam)
#
# x = GDP per person (log), y = CO2 per person (log), area = population,
# color = continent. Everything is driven by the shared SelectionModel:
#   year      -> moves the bubbles (play = stepping the year)
#   basis     -> y is territorial or consumption-based CO2
#   continent -> countries outside it are greyed out and cannot be picked
#   selected  -> selected countries keep their color, the rest turn grey (HW2),
#                and each selected country shows its path since 1990
#
# Built from our homework code:
#   HW1  category -> color dictionary
#   HW2  BubblePanel (QWidget holding figure + canvas), RectangleSelector brushing,
#        "near-zero drag clears the selection", grey EXCLUDED_COLOR for unselected points
#   HW3  SizeLegend / fmt_number, node_areas-style sizing, build artists once and
#        update them with set_offsets, blit-based HoverTooltip (red ring + box that
#        flips toward the centre), now shared by all views in tooltip.py. The hit
#        test works in pixels via transData because our axes are log-scaled
#        (HW3 assumed linear lon/lat axes).
import math

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from matplotlib.widgets import RectangleSelector
from PyQt5 import QtWidgets

from selection import BaseView, CONTINENTS, YEAR_MIN, YEAR_MAX
from tooltip import (CONTINENT_COLORS, EXCLUDED_COLOR, SELECTED_LW, UNSELECTED_LW,
                     HoverTooltip, country_text, rgb as _rgb)

# Continent colors, grey for excluded points and the hover tooltip are the team's
# shared style (tooltip.py), so every view highlights the same way.

X_LIM = (300, 200_000)     # GDP per person, int-$ (2011 prices)
Y_LIM = (0.02, 100)        # tonnes CO2 per person
Y_CAP = Y_LIM[1] * 0.85    # off-scale values (Kuwait 1991 oil fires) are pinned here

# HW3 node_areas: area (points^2) proportional to the value
BUBBLE_MIN_AREA = 8.0
BUBBLE_MAX_AREA = 2600.0
MAX_POPULATION = 1.45e9

CLICK_PX = 3               # a drag shorter than this is a click


def bubble_areas(population):
    pop = np.nan_to_num(np.asarray(population, float), nan=0.0)
    return BUBBLE_MIN_AREA + (BUBBLE_MAX_AREA - BUBBLE_MIN_AREA) * pop / MAX_POPULATION


def fmt_number(v):    # HW3
    return f'{v:.0f}' if float(v).is_integer() else f'{v:.1f}'


def fmt_money(v, _pos=None):
    return f'${v / 1000:g}k' if v >= 1000 else f'${v:g}'


class SizeLegend:     # HW3

    def __init__(self, stops, sizes, ax, title=None, shape='o', facecolor='white',
                 edgecolor='black', anchor=(1.01, 1.0)):
        self.stops = stops
        self.size_stops = np.asarray(sizes, float)
        self.labels = [fmt_number(s) for s in stops]
        handles = [plt.Line2D([], [], linestyle='none', marker=shape,
                              markersize=math.sqrt(s), markerfacecolor=facecolor,
                              markeredgecolor=edgecolor)
                   for s in self.size_stops]
        self.size_legend = ax.legend(handles, self.labels, title=title,
                                     title_fontproperties={'weight': 'bold'},
                                     loc='upper left', bbox_to_anchor=anchor,
                                     handletextpad=1.5, labelspacing=2.0, borderpad=1.0)


def continent_legend(ax, anchor=(1.01, 0.52)):   # same pattern as HW3 node_color_legend
    handles = [plt.Line2D([], [], linestyle='none', marker='o', markersize=8,
                          markerfacecolor=CONTINENT_COLORS[c], markeredgecolor='black')
               for c in CONTINENTS]
    return ax.legend(handles, CONTINENTS, title='Continent',
                     title_fontproperties={'weight': 'bold'}, loc='upper left',
                     bbox_to_anchor=anchor)


class BubblePanel(QtWidgets.QWidget, BaseView):
    """HW2-style panel: a QWidget holding self.figure and self.canvas.

    Team interface: draw(df) once, update_view(state) on every change. (QWidget
    already has update() and the canvas already has draw(), hence these names.)
    """

    def __init__(self, model, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        BaseView.__init__(self, model)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(11, 7))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=1)
        self.ax = None
        self.labels = []

    # ------------------------------------------------------------------ draw
    def draw(self, df):
        """Precompute one (countries x years) array per variable, build artists once."""
        df = df[df['continent'].isin(CONTINENTS)]
        codes = df.dropna(subset=['gdp_pc', 'co2_pc', 'population'])['iso3'].unique()
        df = df[df['iso3'].isin(codes)]
        # largest first, so small bubbles are drawn on top (HW3 draws largest last
        # for nodes on a map; here big bubbles would hide small ones)
        order = df.groupby('iso3')['population'].max().sort_values(ascending=False).index
        years = np.arange(YEAR_MIN, YEAR_MAX + 1)

        def grid(col):
            return (df.pivot_table(index='iso3', columns='year', values=col, aggfunc='first')
                    .reindex(index=order, columns=years).to_numpy(float))

        meta = df.drop_duplicates('iso3').set_index('iso3').loc[order]
        self.iso = np.array(order)
        self.names = meta['country'].to_numpy()
        self.cont = meta['continent'].to_numpy()
        self.X, self.YT, self.YC, self.P = grid('gdp_pc'), grid('co2_pc'), grid('cons_co2_pc'), grid('population')
        self.colors = np.array([[*_rgb(CONTINENT_COLORS[c]), 1.0] for c in self.cont])

        self._build_plot()
        self.update_view(self.model.state)

    def _build_plot(self):
        self.ax = ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.09, right=0.72, top=0.93, bottom=0.10)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlim(*X_LIM)
        ax.set_ylim(*Y_LIM)
        ax.xaxis.set_major_locator(FixedLocator([500, 1000, 2000, 5000, 10_000, 20_000, 50_000, 100_000]))
        ax.xaxis.set_major_formatter(FuncFormatter(fmt_money))
        ax.yaxis.set_major_locator(FixedLocator([0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50]))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f'{v:g}'))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_minor_locator(NullLocator())
        ax.grid(True, color='#e6e6e6', linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlabel('GDP per person (international $, 2011 prices, log scale)')

        self.year_text = ax.text(0.5, 0.42, '', transform=ax.transAxes, ha='center', va='center',
                                 fontsize=110, color='black', alpha=0.06, weight='bold', zorder=0)
        self.note_text = ax.text(0.01, 0.99, '', transform=ax.transAxes, ha='left', va='top',
                                 fontsize=8.5, color='#555555')

        n = len(self.iso)
        self.trails = LineCollection([], linewidths=1.4, alpha=0.85, zorder=3)
        ax.add_collection(self.trails)
        self.bubbles = ax.scatter(np.full(n, np.nan), np.full(n, np.nan), s=bubble_areas(np.zeros(n)),
                                  edgecolors='black', linewidths=0.5, zorder=2)

        # legends (HW3): population in millions, then continent colors
        stops = [10, 100, 1000]
        size_legend = SizeLegend(stops, bubble_areas(np.array(stops) * 1e6), ax,
                                 title='Population (millions)')
        ax.add_artist(size_legend.size_legend)
        ax.add_artist(continent_legend(ax))
        self.figure.text(0.735, 0.10, 'Drag: select countries\nShift+drag: add to selection\n'
                                      'Click bubble: toggle\nClick empty: clear',
                         fontsize=8.5, color='#666666', va='bottom')

        self.tooltip = HoverTooltip(self.figure, ax, node_text=self._tooltip_text)
        self.selector = RectangleSelector(ax, self._on_select, useblit=False, button=[1],
                                          minspanx=0, minspany=0, spancoords='data',
                                          interactive=False)

    # ---------------------------------------------------------------- update
    def update_view(self, state):
        if self.ax is None:
            return  # draw(df) has not run yet
        j = state.year - YEAR_MIN
        consumption = state.basis == 'consumption'
        x, pop = self.X[:, j], self.P[:, j]
        y = (self.YC if consumption else self.YT)[:, j]
        valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(pop) & (x > 0) & (y > 0)
        capped = valid & (y > Y_CAP)
        y_plot = np.where(capped, Y_CAP, y)
        in_cont = np.ones(len(self.iso), bool) if state.continent is None else (self.cont == state.continent)
        selected = np.isin(self.iso, list(state.selected))
        pickable = valid & in_cont

        # HW2: with a selection, unselected points turn grey; continent filter greys too
        face = self.colors.copy()
        face[:, 3] = 0.75
        grey = (~selected if selected.any() else np.zeros(len(self.iso), bool)) | ~in_cont
        face[grey] = [*EXCLUDED_COLOR, 0.4]
        face[~in_cont, 3] = 0.15
        face[selected & in_cont, 3] = 0.95

        areas = bubble_areas(pop)
        self.bubbles.set_offsets(np.column_stack([np.where(valid, x, np.nan), np.where(valid, y_plot, np.nan)]))
        self.bubbles.set_sizes(areas)
        self.bubbles.set_facecolors(face)
        self.bubbles.set_edgecolors(np.where(grey[:, None], [[0, 0, 0, 0]], [[0, 0, 0, 1]]))
        self.bubbles.set_linewidths(np.where(selected, SELECTED_LW, UNSELECTED_LW))

        self._cur = dict(j=j, x=x, y=y, y_plot=y_plot, valid=valid, capped=capped,
                         pickable=pickable, state=state)
        self._draw_trails(state, j, consumption)
        self._update_text(state, j, consumption, valid, capped)

        ids = np.flatnonzero(pickable)
        self.tooltip.set_data(np.column_stack([x[ids], y_plot[ids]]), areas[ids], ids)
        self.canvas.draw_idle()

    def _draw_trails(self, state, j, consumption):
        for t in self.labels:
            t.remove()
        self.labels = []
        Y = self.YC if consumption else self.YT
        chosen = np.flatnonzero(np.isin(self.iso, list(state.selected)))
        # alternate labels above/below in order of height so neighbours don't collide
        chosen = chosen[np.argsort(np.nan_to_num(self._cur['y_plot'][chosen], nan=0.0))]
        paths, colors = [], []
        for rank, i in enumerate(chosen):
            pts = np.column_stack([self.X[i, :j + 1], np.minimum(Y[i, :j + 1], Y_CAP)])
            pts = pts[np.isfinite(pts).all(axis=1)]
            if len(pts) > 1:
                paths.append(pts)
                colors.append(CONTINENT_COLORS[self.cont[i]])
            if self._cur['valid'][i]:
                offset = (7, 7) if rank % 2 == 0 else (7, -13)
                self.labels.append(self.ax.annotate(
                    self.names[i], (self._cur['x'][i], self._cur['y_plot'][i]), xytext=offset,
                    textcoords='offset points', fontsize=9, weight='bold', zorder=4))
        self.trails.set_segments(paths)
        self.trails.set_color(colors)
        for i in np.flatnonzero(self._cur['capped']):
            self.labels.append(self.ax.annotate(
                f'↑ {self.names[i]}', (self._cur['x'][i], Y_CAP), xytext=(6, -3),
                textcoords='offset points', fontsize=8.5, color='#444444', zorder=4))

    def _update_text(self, state, j, consumption, valid, capped):
        what = 'Consumption-based' if consumption else 'Territorial'
        self.year_text.set_text(str(state.year))
        self.ax.set_ylabel(f'{what} CO₂ per person (tonnes, log scale)')
        self.ax.set_title(f'Wealth vs Emissions, {state.year} ({what.lower()} CO₂)', weight='bold')
        notes = []
        if consumption:
            has_terr = np.isfinite(self.YT[:, j]) & np.isfinite(self.X[:, j])
            notes.append(f'{int((has_terr & ~valid).sum())} countries hidden: no consumption-based estimate')
        for i in np.flatnonzero(capped):
            notes.append(f'{self.names[i]} {state.year}: {self._cur["y"][i]:.0f} t/person, '
                         f'off scale (drawn at top edge)')
        self.note_text.set_text('\n'.join(notes))

    # ----------------------------------------------------------- interaction
    def _tooltip_text(self, i):
        c = self._cur
        j = c['j']
        extra = [('Off scale', 'drawn at top edge')] if c['capped'][i] else []
        return country_text(self.names[i], c['state'].year, self.cont[i], self.YT[i, j],
                            self.YC[i, j], c['x'][i], self.P[i, j], extra)

    def _on_select(self, eclick, erelease):
        # HW2: a near-zero drag is a click. Here a click on a bubble toggles it,
        # a click on empty space clears the selection.
        if abs(erelease.x - eclick.x) < CLICK_PX and abs(erelease.y - eclick.y) < CLICK_PX:
            k = self.tooltip.hit(eclick.x, eclick.y)
            if k is None:
                self.model.clear_selection()
            else:
                self.model.toggle(self.iso[self.tooltip.node_ids[k]])
            return
        if None in (eclick.xdata, erelease.xdata, eclick.ydata, erelease.ydata):
            return  # released outside the axes
        x0, x1 = sorted([eclick.xdata, erelease.xdata])
        y0, y1 = sorted([eclick.ydata, erelease.ydata])
        c = self._cur
        inside = (c['pickable'] & (c['x'] >= x0) & (c['x'] <= x1)
                  & (c['y_plot'] >= y0) & (c['y_plot'] <= y1))
        if eclick.key == 'shift':
            self.model.add_selected(self.iso[inside])
        else:
            self.model.set_selected(self.iso[inside])

