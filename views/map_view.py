"""View A: world map choropleth (owner: Shloka Kandukuri).

Follows the BaseView contract from selection.py: draw(df) once, update_view(state)
on every change. The year slider just changes the SelectionModel; this view
recolors its single PatchCollection with set_array, so it stays responsive.

Weeks 1-2: choropleth of CO2 (territorial or consumption basis) recolored by year,
no-data countries in grey, continent filter dims other continents, selected
countries get a dark outline. Click a country to toggle it in the shared
selection, click the ocean to clear it (same rule as view B), so selecting in A
highlights in every other view. Metric menu, diverging scale and tooltips come in
weeks 3-4.
"""
import matplotlib
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from PyQt5 import QtWidgets

from map_geometry import build_collection, load_countries, report_unmatched
from selection import YEAR_MAX, YEAR_MIN, BaseView

NO_DATA = '#cfcfcf'
# metric -> {basis: column in the shared table}. Weeks 3-4: add per person, per GDP, ...
METRICS = {'total': {'territorial': 'co2', 'consumption': 'cons_co2'}}
BASIS_LABEL = {'territorial': 'Territorial', 'consumption': 'Consumption-based'}


class MapPanel(QtWidgets.QWidget, BaseView):
    def __init__(self, model, map_file, parent=None):
        super().__init__(parent)
        BaseView.__init__(self, model)
        self.world = load_countries(map_file)
        self.collection = None
        self.metric = 'total'
        self.in_table = np.zeros(len(self.world), bool)

        self.figure = Figure(figsize=(11, 5.5))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.canvas.mpl_connect('button_press_event', self._on_click)

    def draw(self, df):
        countries = self.world['iso3'].tolist()
        report_unmatched(df['iso3'].unique(), self.world)
        self.in_table = self.world['iso3'].isin(df['iso3']).to_numpy()

        # country x year grids, aligned to the patch order
        years = list(range(YEAR_MIN, YEAR_MAX + 1))
        self.grids = {}
        for col in {c for m in METRICS.values() for c in m.values()}:
            grid = df.pivot(index='iso3', columns='year', values=col)
            self.grids[col] = grid.reindex(index=countries, columns=years).to_numpy(float)

        # one fixed log scale for all years and both bases, so frames are comparable
        pos = np.concatenate([g[np.isfinite(g) & (g > 0)] for g in self.grids.values()])
        self.vmin, vmax = np.percentile(pos, 1), pos.max()
        norm = LogNorm(vmin=self.vmin, vmax=vmax, clip=True)
        cmap = matplotlib.colormaps['YlOrRd'].copy()
        cmap.set_bad(NO_DATA)

        self.collection = build_collection(self.world, cmap=cmap, norm=norm,
                                           edgecolor='#555555', linewidth=0.3)
        self.ax.add_collection(self.collection)
        self.ax.set_xlim(-180, 180)
        self.ax.set_ylim(-58, 85)
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        self.colorbar = self.figure.colorbar(self.collection, ax=self.ax,
                                             fraction=0.025, pad=0.01)
        self.figure.tight_layout()
        self.update_view(self.model.state)

    def update_view(self, state):
        if self.collection is None:  # model changed before draw()
            return
        col = METRICS[self.metric][state.basis]
        values = self.grids[col][:, state.year - YEAR_MIN]
        values = np.where(np.isfinite(values), np.maximum(values, self.vmin), np.nan)
        self.collection.set_array(np.ma.masked_invalid(values))

        # continent filter fades the rest; selection gets a dark outline
        in_continent = (np.ones(len(self.world), bool) if state.continent is None
                        else (self.world['continent'] == state.continent).to_numpy())
        self.collection.set_alpha(np.where(in_continent, 1.0, 0.25))
        selected = self.world['iso3'].isin(state.selected).to_numpy()
        self.collection.set_edgecolor(np.where(selected, 'black', '#555555'))
        self.collection.set_linewidth(np.where(selected, 1.4, 0.3))

        label = f'{BASIS_LABEL[state.basis]} CO₂ (million tonnes)'
        self.colorbar.set_label(label)
        self.ax.set_title(f'{label}, {state.year}')
        self.canvas.draw_idle()

    # ------------------------------------------------------------ interaction
    def country_at(self, event):
        """Row in self.world of the country under the mouse, or None (HW3 picking)."""
        if self.collection is None or event.inaxes is not self.ax:
            return None
        hit, info = self.collection.contains(event)
        if not hit:
            return None
        state = self.model.state
        for i in info['ind'][::-1]:   # the last one drawn is on top
            in_continent = state.continent is None or self.world['continent'].iat[i] == state.continent
            if self.in_table[i] and in_continent:
                return int(i)
        return None

    def _on_click(self, event):
        if event.button != 1 or event.inaxes is not self.ax:
            return
        i = self.country_at(event)
        if i is None:
            self.model.clear_selection()
        else:
            self.model.toggle(self.world['iso3'].iat[i])
