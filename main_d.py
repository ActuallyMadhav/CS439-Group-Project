# run command: python3 main_d.py -i owid-co2-data.csv -m ne_50m_admin_0_countries.geojson
#   optional: -e owid-energy-data.csv (default: next to the CO2 file)
#             --year 2022 --continent Europe --select GBR,SWE
#             --screenshot out.png   (saves the chart and exits, for the report)
#
# Stand-alone window for view D (owner: Tanisha Phadke). Reuses the shared ControlBar
# from main_b so all views behave the same.
import sys
import argparse

from PyQt5 import QtWidgets

from data import load_table
from main_b import ControlBar
from selection import CONTINENTS, YEAR_MAX, SelectionModel
from views.outsourcing_view import OutsourcingPanel


class OutsourcingWindow(QtWidgets.QMainWindow):
    def __init__(self, df, model):
        super().__init__()
        self.setWindowTitle('Did Rich Countries Really Cut Their Emissions? - View D')
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.controls = ControlBar(model)
        self.panel = OutsourcingPanel(model)
        layout.addWidget(self.controls)
        layout.addWidget(self.panel, stretch=1)
        self.panel.draw(df)
        self.resize(1100, 850)


def run_window(args):   # HW3
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    df = load_table(args.input, args.map_file, args.energy)
    model = SelectionModel()
    window = OutsourcingWindow(df, model)
    model.set_year(args.year)
    model.set_continent(args.continent)
    model.set_selected([c.strip().upper() for c in args.select.split(',') if c.strip()])

    if args.screenshot:
        window.panel.canvas.draw()
        window.panel.figure.savefig(args.screenshot, dpi=130)
        print(f'saved {args.screenshot}')
        return
    window.show()
    app.exec_()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Outsourced emissions: territorial vs consumption CO2')
    parser.add_argument('-i', '--input', dest='input', required=True, help='owid-co2-data.csv')
    parser.add_argument('-m', '--map', dest='map_file', required=True, help='world map (GeoJSON)')
    parser.add_argument('-e', '--energy', default=None, help='owid-energy-data.csv')
    parser.add_argument('--year', type=int, default=YEAR_MAX)
    parser.add_argument('--continent', choices=CONTINENTS, default=None)
    parser.add_argument('--select', default='', help='ISO-3 codes, e.g. GBR,SWE')
    parser.add_argument('--screenshot', help='save the chart to this PNG and exit')
    args = parser.parse_args()

    run_window(args)
