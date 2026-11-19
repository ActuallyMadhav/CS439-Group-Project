"""View A: world map choropleth (owner: Shloka Kandukuri).

Follows the BaseView contract from selection.py: draw(df) once, update_view(state)
on every change. The year slider just changes the SelectionModel; this view
recolors its single PatchCollection with set_array, so it stays responsive.

Weeks 1-2: choropleth of CO2 (territorial or consumption basis) recolored by year,
no-data countries in grey, continent filter dims other continents, selected
countries get a dark outline. Click-to-select, metric menu, diverging scale and
tooltips come in weeks 3-4.
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

        self.figure = Figure(figsize=(11, 5.5))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

    def draw(self, df):
        countries = self.world['iso3'].tolist()
        report_unmatched(df['iso3'].unique(), self.world)

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