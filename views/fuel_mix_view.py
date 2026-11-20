"""View E: stacked CO2-by-fuel area and low-carbon electricity share."""
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

FUELS = [('coal_co2', 'Coal'), ('oil_co2', 'Oil'), ('gas_co2', 'Gas'),
         ('cement_co2', 'Cement'), ('flaring_co2', 'Flaring')]


class FuelMixPanel(QtWidgets.QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.df = None
        self.figure = Figure(figsize=(11, 5), constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.country_combo = QtWidgets.QComboBox()
        self.country_combo.currentIndexChanged.connect(self._choose_country)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('View E · Fuel CO₂ emissions and low-carbon electricity'))
        layout.addWidget(self.country_combo)
        layout.addWidget(self.canvas)
        model.changed.connect(self.update_view)

    def draw(self, df):
        self.df = df.copy()
        self.update_view(self.model.state)

    def _choose_country(self, index):
        if index >= 0:
            code = self.country_combo.itemData(index)
            if code:
                self.model.set_selected([code])
            else:
                self.model.clear_selection()

    def update_view(self, state):
        if self.df is None:
            return
        codes = sorted(set(state.selected))
        # Show the first selected country, with a chooser if several are selected.
        available = self.df.loc[self.df.iso3.isin(codes), ['iso3', 'country']].drop_duplicates()
        entries = [('', 'World')] + [(r.iso3, r.country) for r in available.itertuples()]
        current = self.country_combo.currentData()
        preferred = current if current in codes else (codes[0] if codes else '')
        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        for code, label in entries:
            self.country_combo.addItem(label, code)
        self.country_combo.setCurrentIndex(next((i for i, (code, _) in enumerate(entries) if code == preferred), 0))
        self.country_combo.setVisible(len(entries) > 2)
        self.country_combo.blockSignals(False)
        code = preferred if codes else 'OWID_WRL'
        subset = self.df.loc[self.df.iso3 == code].sort_values('year')
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if subset.empty:
            ax.text(.5, .5, 'No data available', ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw_idle()
            return
        years = subset.year.to_numpy()
        cols = [(key, label) for key, label in FUELS if key in subset]
        values = [pd.to_numeric(subset[key], errors='coerce').clip(lower=0).fillna(0).to_numpy() for key, _ in cols]
        if values:
            ax.stackplot(years, *values, labels=[label for _, label in cols], alpha=.85)
        ax.set_xlabel('Year')
        ax.set_ylabel('Fuel CO₂ emissions (million tonnes)')
        ax.set_xlim(years.min(), years.max())
        ax.axvline(state.year, color='black', linestyle=':', linewidth=1, label=f'Selected year: {state.year}')
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
        self.canvas.draw_idle()
