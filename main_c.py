# run command: python3 main_c.py -i owid-co2-data.csv -m ne_50m_admin_0_countries.geojson
#   optional: --year 2022 --basis consumption --continent Europe --select GBR,SWE,USA,CHN
#             --screenshot out.png   (saves the chart and exits, for the report)
#
# Stand-alone window for view C (owner: Shivam Rastogi). Reuses the shared ControlBar
# (year slider + play, basis, continent, reset) from main_b so every view behaves the same.
# View C has no selection gesture of its own: it follows the selection made in A, B or D.
# Here, use --select (or the country box below the controls) to choose countries.
import sys
import argparse

from PyQt5 import QtWidgets

from data import load_table
from main_b import ControlBar
from metrics import add_metrics
from selection import CONTINENTS, YEAR_MAX, SelectionModel
from views.decoupling_view import DecouplingPanel


class DecouplingWindow(QtWidgets.QMainWindow):
    def __init__(self, df, model):
        super().__init__()
        self.setWindowTitle('Did Rich Countries Really Cut Their Emissions? - View C')
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.controls = ControlBar(model)
        layout.addWidget(self.controls)

        # stand-in for the other views' selection: type ISO-3 codes
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel('Countries (ISO-3, comma separated)'))
        self.select_box = QtWidgets.QLineEdit()
        self.select_box.setPlaceholderText('e.g. GBR,SWE,USA,CHN')
        self.select_box.returnPressed.connect(
            lambda: model.set_selected(c.strip().upper() for c in self.select_box.text().split(',')
                                       if c.strip()))
        row.addWidget(self.select_box, stretch=1)
        layout.addLayout(row)

        self.panel = DecouplingPanel(model)
        layout.addWidget(self.panel, stretch=1)
        self.panel.draw(df)
        model.changed.connect(lambda s: self.select_box.setText(','.join(sorted(s.selected))))
        self.resize(1300, 850)


def run_window(args):   # HW3
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    df = add_metrics(load_table(args.input, args.map_file))
    model = SelectionModel()
    window = DecouplingWindow(df, model)
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
    parser = argparse.ArgumentParser(description='Decoupling chart: GDP vs CO2, 1990 = 100')
    parser.add_argument('-i', '--input', dest='input', required=True, help='owid-co2-data.csv')
    parser.add_argument('-m', '--map', dest='map_file', required=True, help='world map (GeoJSON)')
    parser.add_argument('--year', type=int, default=YEAR_MAX)
    parser.add_argument('--basis', choices=['territorial', 'consumption'], default='territorial')
    parser.add_argument('--continent', choices=CONTINENTS, default=None)
    parser.add_argument('--select', default='', help='ISO-3 codes, e.g. GBR,SWE')
    parser.add_argument('--screenshot', help='save the chart to this PNG and exit')
    args = parser.parse_args()

    run_window(args)
