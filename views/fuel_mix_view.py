"""View E: stacked CO2-by-fuel area and low-carbon electricity share (owner: Saanvi Khemka).

Follows the BaseView contract from selection.py: draw(df) once, update_view(state)
on every change.
  selected -> shows one selected country; with several selected, a dropdown picks
              which one. The dropdown is local to this view: it does NOT change the
              shared selection, so the other views keep all selected countries.
  nothing selected -> shows the World.
  year     -> a dotted marker follows the year slider. Only the marker moves on a
              year change, so play stays smooth (the chart is rebuilt only when the
              shown country changes).
Basis and continent do not apply to this view (fuel series are territorial).
"""
import pandas as pd
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from data import WORLD
from selection import BaseView

FUELS = [('coal_co2', 'Coal'), ('oil_co2', 'Oil'), ('gas_co2', 'Gas'),
         ('cement_co2', 'Cement'), ('flaring_co2', 'Flaring')]


class FuelMixPanel(QtWidgets.QWidget, BaseView):
    def __init__(self, model, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        BaseView.__init__(self, model)
        self.df = None
        self.shown = None        # iso3 currently drawn
        self.choice = None       # country picked in the dropdown (local to this view)
        self.year_line = None
        self.figure = Figure(figsize=(11, 5), constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.country_combo = QtWidgets.QComboBox()
        self.country_combo.currentIndexChanged.connect(self._choose_country)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('View E · Fuel CO₂ emissions and low-carbon electricity'))
        layout.addWidget(self.country_combo)
        layout.addWidget(self.canvas)

    def draw(self, df):
        self.df = df.copy()
        self.update_view(self.model.state)

    def _choose_country(self, index):
        if index >= 0:
            self.choice = self.country_combo.itemData(index)
            self.update_view(self.model.state)

    def update_view(self, state):
        if self.df is None:
            return
        codes = sorted(set(state.selected))
        available = self.df.loc[self.df.iso3.isin(codes), ['iso3', 'country']].drop_duplicates()
        entries = [(WORLD, 'World')] + [(r.iso3, r.country) for r in available.itertuples()]
        valid = [code for code, _ in entries]
        if self.choice not in valid:
            self.choice = None
        code = self.choice or (available.iso3.iloc[0] if len(available) else WORLD)

        # dropdown follows the selection without emitting (blockSignals, as in HW3)
        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        for item_code, label in entries:
            self.country_combo.addItem(label, item_code)
        self.country_combo.setCurrentIndex(valid.index(code))
        self.country_combo.setVisible(len(entries) > 2)
        self.country_combo.blockSignals(False)

        if code == self.shown and self.year_line is not None:
            self.year_line.set_xdata([state.year, state.year])   # year change only
        else:
            self._build(code, state.year)
        self.canvas.draw_idle()

    def _build(self, code, year):
        self.shown = code
        self.year_line = None
        subset = self.df.loc[self.df.iso3 == code].sort_values('year')
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if subset.empty:
            ax.text(.5, .5, 'No data available', ha='center', va='center', transform=ax.transAxes)
            return
        years = subset.year.to_numpy()
        cols = [(key, label) for key, label in FUELS if key in subset]
        values = [pd.to_numeric(subset[key], errors='coerce').clip(lower=0).fillna(0).to_numpy() for key, _ in cols]
        if values:
            ax.stackplot(years, *values, labels=[label for _, label in cols], alpha=.85)
        ax.set_xlabel('Year')
        ax.set_ylabel('Fuel CO₂ emissions (million tonnes)')
        ax.set_xlim(years.min(), years.max())
        self.year_line = ax.axvline(year, color='black', linestyle=':', linewidth=1)
        ax2 = ax.twinx()
        if 'low_carbon_share_elec' in subset:
            share = pd.to_numeric(subset.low_carbon_share_elec, errors='coerce')
            ax2.plot(years, share, color='black', linewidth=2.5, label='Low-carbon electricity share')
        ax2.set_ylabel('Low-carbon electricity share (%)')
        ax2.set_ylim(0, 100)
        ax.set_title(f'{subset.country.iloc[0]} · CO₂ by fuel and low-carbon electricity')
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=8, ncol=2)
