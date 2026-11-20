# run command: python3 main.py -i data/raw/owid-co2-data.csv -m data/raw/ne_50m_admin_0_countries.geojson
#   optional: -e owid-energy-data.csv (default: next to the CO2 file)
#             --year 2022 --basis consumption --continent Europe --select GBR,SWE
#             --screenshot out.png   (saves the whole window and exits, for the report)
#
# The team's main window: one shared SelectionModel, the shared ControlBar (main_b)
# and the five linked views laid out as in the proposal's sketch 1:
#     A world map        | B wealth vs emissions
#     C decoupling       | D outsourced emissions
#     E fuel and electricity mix (full width)
# Views never talk to each other: each one listens to the model (selection.py).
import sys
import argparse

from PyQt5 import QtCore, QtGui, QtWidgets

from data import load_table
from main_b import ControlBar
from metrics import add_metrics
from selection import CONTINENTS, YEAR_MAX, SelectionModel
from views.bubble_view import BubblePanel
from views.decoupling_view import DecouplingPanel
from views.fuel_mix_view import FuelMixPanel
from views.map_view import MapPanel
from views.outsourcing_view import OutsourcingPanel

ROW_HEIGHT = 560      # pixels per row of views; the window scrolls vertically
TITLE = 'Did Rich Countries Really Cut Their Emissions?'


def framed(title, panel):
    """Panel with a bold caption, so the user can tell the five views apart."""
    box = QtWidgets.QGroupBox(title)
    box.setStyleSheet('QGroupBox { font-weight: bold; }')
    layout = QtWidgets.QVBoxLayout(box)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.addWidget(panel)
    return box


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, df, model, map_file):
        super().__init__()
        self.setWindowTitle(TITLE)

        self.controls = ControlBar(model)
        self.panels = {
            'A': MapPanel(model, map_file),
            'B': BubblePanel(model),
            'C': DecouplingPanel(model),
            'D': OutsourcingPanel(model),
            'E': FuelMixPanel(model),
        }
        titles = {'A': 'A · World map', 'B': 'B · Wealth vs emissions',
                  'C': 'C · Decoupling (1990 = 100)', 'D': 'D · Outsourced emissions',
                  'E': 'E · Fuel and electricity mix'}

        grid_widget = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_widget)
        for key, row, col, span in (('A', 0, 0, 1), ('B', 0, 1, 1), ('C', 1, 0, 1),
                                    ('D', 1, 1, 1), ('E', 2, 0, 2)):
            grid.addWidget(framed(titles[key], self.panels[key]), row, col, 1, span)
        for row in range(3):
            grid.setRowMinimumHeight(row, ROW_HEIGHT)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.grid_widget = grid_widget

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_widget)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(self.controls)
        layout.addWidget(scroll, stretch=1)
        self.setCentralWidget(central)

        # one table for every view; C needs the derived metrics (metrics.py)
        for key, panel in self.panels.items():
            panel.draw(add_metrics(df) if key == 'C' else df)
        self.resize(1600, 1000)

    def screenshot(self, path):
        """Save the controls and all five views as one PNG."""
        self.grid_widget.resize(self.grid_widget.width(), 3 * ROW_HEIGHT + 40)
        QtWidgets.QApplication.processEvents()
        for panel in self.panels.values():
            panel.canvas.draw()
        QtWidgets.QApplication.processEvents()
        controls = self.controls.grab()
        views = self.grid_widget.grab()
        image = QtCore.QSize(max(controls.width(), views.width()), controls.height() + views.height())
        out = QtGui.QPixmap(image)
        out.fill(QtCore.Qt.white)
        painter = QtGui.QPainter(out)
        painter.drawPixmap(0, 0, controls)
        painter.drawPixmap(0, controls.height(), views)
        painter.end()
        out.save(path)


def run_window(args):   # HW3
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    df = load_table(args.input, args.map_file, args.energy)
    model = SelectionModel()
    window = MainWindow(df, model, args.map_file)
    model.set_year(args.year)
    model.set_basis(args.basis)
    model.set_continent(args.continent)
    model.set_selected([c.strip().upper() for c in args.select.split(',') if c.strip()])

    if args.screenshot:
        window.show()
        window.screenshot(args.screenshot)
        print(f'saved {args.screenshot}')
        return
    window.show()
    app.exec_()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument('-i', '--input', dest='input', required=True, help='owid-co2-data.csv')
    parser.add_argument('-m', '--map', dest='map_file', required=True, help='world map (GeoJSON)')
    parser.add_argument('-e', '--energy', default=None, help='owid-energy-data.csv')
    parser.add_argument('--year', type=int, default=YEAR_MAX)
    parser.add_argument('--basis', choices=['territorial', 'consumption'], default='territorial')
    parser.add_argument('--continent', choices=CONTINENTS, default=None)
    parser.add_argument('--select', default='', help='ISO-3 codes, e.g. GBR,SWE')
    parser.add_argument('--screenshot', help='save the whole window to this PNG and exit')
    args = parser.parse_args()

    run_window(args)
