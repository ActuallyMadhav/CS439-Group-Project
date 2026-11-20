"""Standalone View E integrated with the team's SelectionModel and ControlBar."""
import argparse
import sys
from PyQt5 import QtWidgets
from data import load_table
from main_b import ControlBar
from selection import SelectionModel
from views.fuel_mix_view import FuelMixPanel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='OWID CO2 CSV')
    parser.add_argument('-e', '--energy', required=True, help='OWID energy CSV')
    parser.add_argument('-m', '--map', required=True, dest='map_file', help='Natural Earth GeoJSON')
    parser.add_argument('--select', default='', help='Selected ISO3 country codes, comma-separated')
    parser.add_argument('--screenshot', help='Save chart to PNG instead of launching window')
    args = parser.parse_args()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    model = SelectionModel()
    df = load_table(args.input, args.map_file, args.energy)
    window = QtWidgets.QMainWindow()
    window.setWindowTitle('CS439 · View E · Fuel and Electricity Mix')
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    layout.addWidget(ControlBar(model))
    panel = FuelMixPanel(model)
    layout.addWidget(panel)
    window.setCentralWidget(widget)
    panel.draw(df)
    if args.select:
        model.set_selected([s.strip().upper() for s in args.select.split(',') if s.strip()])
    if args.screenshot:
        panel.canvas.draw()
        panel.figure.savefig(args.screenshot, dpi=160)
        print('Saved', args.screenshot)
        return
    window.resize(1250, 700)
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
