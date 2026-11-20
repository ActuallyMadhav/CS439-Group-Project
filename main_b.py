# run command: python3 main_b.py -i owid-co2-data.csv -m ne_50m_admin_0_countries.geojson
#   optional: --year 2022 --basis consumption --continent Europe --select GBR,SWE
#             --screenshot out.png   (saves the chart and exits, for the report)
#
# Stand-alone window for view B plus the shared control bar (owner: Madhav Anantharam).
# ControlBar only talks to the SelectionModel, so the team's main window can reuse it
# and place the other four views next to the bubble chart.
import sys
import argparse

from PyQt5 import QtWidgets, QtCore

from data import load_table
from selection import CONTINENTS, YEAR_MAX, YEAR_MIN, SelectionModel
from views.bubble_view import BubblePanel

ALL_CONTINENTS = 'All'
BASES = [('Territorial CO₂', 'territorial'), ('Consumption-based CO₂', 'consumption')]
FRAME_MS = 250  # play speed: 4 years per second


class ControlBar(QtWidgets.QWidget):
    """HW3-style grid of controls: play, year slider + label, basis, continent, reset."""

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        grid = QtWidgets.QGridLayout(self)

        self.play_button = QtWidgets.QPushButton('▶ Play')
        self.year_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.year_slider.setRange(YEAR_MIN, YEAR_MAX)
        self.year_label = QtWidgets.QLabel()
        self.year_label.setMinimumWidth(60)
        self.basis_combo = QtWidgets.QComboBox()
        self.basis_combo.addItems([label for label, _ in BASES])
        self.continent_combo = QtWidgets.QComboBox()
        self.continent_combo.addItems([ALL_CONTINENTS] + list(CONTINENTS))
        self.reset_button = QtWidgets.QPushButton('Reset')

        grid.addWidget(self.play_button, 0, 0)
        grid.addWidget(QtWidgets.QLabel('Year'), 0, 1)
        grid.addWidget(self.year_slider, 0, 2)
        grid.addWidget(self.year_label, 0, 3)
        grid.addWidget(QtWidgets.QLabel('Basis'), 0, 4)
        grid.addWidget(self.basis_combo, 0, 5)
        grid.addWidget(QtWidgets.QLabel('Continent'), 0, 6)
        grid.addWidget(self.continent_combo, 0, 7)
        grid.addWidget(self.reset_button, 0, 8)
        grid.setColumnStretch(2, 1)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(FRAME_MS)
        self.timer.timeout.connect(self._on_tick)

        self.play_button.clicked.connect(self._on_play)
        self.year_slider.valueChanged.connect(model.set_year)
        self.basis_combo.currentIndexChanged.connect(lambda i: model.set_basis(BASES[i][1]))
        self.continent_combo.currentTextChanged.connect(
            lambda t: model.set_continent(None if t == ALL_CONTINENTS else t))
        self.reset_button.clicked.connect(self._on_reset)
        model.changed.connect(self.sync)
        self.sync(model.state)

    def sync(self, state):
        """Follow the model without re-emitting (blockSignals, as in HW3)."""
        for widget, setter, value in (
                (self.year_slider, self.year_slider.setValue, state.year),
                (self.basis_combo, self.basis_combo.setCurrentIndex,
                 [b for _, b in BASES].index(state.basis)),
                (self.continent_combo, self.continent_combo.setCurrentText,
                 state.continent or ALL_CONTINENTS)):
            widget.blockSignals(True)
            setter(value)
            widget.blockSignals(False)
        self.year_label.setText(str(state.year))

    def _on_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText('▶ Play')
            return
        if self.model.state.year >= YEAR_MAX:
            self.model.set_year(YEAR_MIN)  # restart from 1990
        self.timer.start()
        self.play_button.setText('⏸ Pause')

    def _on_tick(self):
        if self.model.state.year >= YEAR_MAX:
            self._on_play()  # stop at the last year
        else:
            self.model.set_year(self.model.state.year + 1)

    def _on_reset(self):
        if self.timer.isActive():
            self._on_play()
        self.model.reset()


class BubbleWindow(QtWidgets.QMainWindow):
    def __init__(self, df, model):
        super().__init__()
        self.setWindowTitle('Did Rich Countries Really Cut Their Emissions? - View B')
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.controls = ControlBar(model)
        self.panel = BubblePanel(model)
        layout.addWidget(self.controls)
        layout.addWidget(self.panel, stretch=1)
        self.panel.draw(df)
        self.resize(1300, 850)


def run_window(args):   # HW3
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    df = load_table(args.input, args.map_file)
    model = SelectionModel()
    window = BubbleWindow(df, model)
    model.set_year(args.year)
    model.set_basis(args.basis)
    model.set_continent(args.continent)
    model.set_selected([c for c in args.select.split(',') if c])

    if args.screenshot:
        window.panel.canvas.draw()
        window.panel.figure.savefig(args.screenshot, dpi=130)
        print(f'saved {args.screenshot}')
        return
    window.show()
    app.exec_()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wealth vs emissions bubble chart')
    parser.add_argument('-i', '--input', dest='input', required=True, help='owid-co2-data.csv')
    parser.add_argument('-m', '--map', dest='map_file', required=True, help='world map (GeoJSON)')
    parser.add_argument('--year', type=int, default=YEAR_MAX)
    parser.add_argument('--basis', choices=['territorial', 'consumption'], default='territorial')
    parser.add_argument('--continent', choices=CONTINENTS, default=None)
    parser.add_argument('--select', default='', help='ISO-3 codes, e.g. GBR,SWE')
    parser.add_argument('--screenshot', help='save the chart to this PNG and exit')
    args = parser.parse_args()

    run_window(args)
