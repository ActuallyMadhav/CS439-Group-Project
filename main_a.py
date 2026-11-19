# run command: python3 main_a.py -i owid-co2-data.csv -m ne_50m_admin_0_countries.geojson
#   optional: --year 2022 --basis consumption --continent Europe --select GBR,SWE
#             --screenshot out.png   (saves the map and exits, for the report)
#
# Stand-alone window for view A (owner: Shloka Kandukuri). Reuses the shared ControlBar
# (year slider + play, basis, continent, reset) from main_b so both views behave the same.
import sys
import argparse

from PyQt5 import QtWidgets

from data_minimal import load_table
from main_b import ControlBar
from selection import CONTINENTS, YEAR_MAX, SelectionModel
from views.map_view import MapPanel


class MapWindow(QtWidgets.QMainWindow):
    def __init__(self, df, model, map_file):
        super().__init__()
        self.setWindowTitle('Did Rich Countries Really Cut Their Emissions? - View A')
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.controls = ControlBar(model)
        self.panel = MapPanel(model, map_file)
        layout.addWidget(self.controls)
        layout.addWidget(self.panel, stretch=1)
        self.panel.draw(df)
        self.resize(1300, 800)


def run_window(args):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    df = load_table(args.input, args.map_file)
    model = SelectionModel()
    window = MapWindow(df, model, args.map_file)
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
    parser = argparse.ArgumentParser(description='World map of CO2 emissions')
    parser.add_argument('-i', '--input', dest='input', required=True, help='owid-co2-data.csv')
    parser.add_argument('-m', '--map', dest='map_file', required=True, help='world map (GeoJSON)')
    parser.add_argument('--year', type=int, default=YEAR_MAX)
    parser.add_argument('--basis', choices=['territorial', 'consumption'], default='territorial')
    parser.add_argument('--continent', choices=CONTINENTS, default=None)
    parser.add_argument('--select', default='', help='ISO-3 codes, e.g. GBR,SWE')
    parser.add_argument('--screenshot', help='save the map to this PNG and exit')
    args = parser.parse_args()

    run_window(args)