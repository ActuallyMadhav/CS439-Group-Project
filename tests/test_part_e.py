"""Tests for view E linking (owner: Saanvi Khemka).

Run headless:
    QT_QPA_PLATFORM=offscreen python tests/test_part_e.py <owid-co2-data.csv> <ne_50m.geojson>
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt5.QtWidgets import QApplication

from data import WORLD, load_table
from selection import SelectionModel, YEAR_MAX, YEAR_MIN
from views.fuel_mix_view import FuelMixPanel


def test_view(df):
    m = SelectionModel()
    v = FuelMixPanel(m)
    v.resize(1100, 500)
    v.draw(df)

    # Nothing selected: the World.
    assert v.shown == WORLD
    assert "World" in v.figure.axes[0].get_title()

    # Follows the selection; with several, the first is shown and the dropdown lists all.
    m.set_selected(["SWE", "GBR"])
    assert v.shown == "GBR"
    assert v.country_combo.count() == 3                  # World + 2 countries

    # Picking another country in the dropdown is local: the shared selection is kept.
    v.country_combo.setCurrentIndex(v.country_combo.findData("SWE"))
    assert v.shown == "SWE"
    assert m.state.selected == {"SWE", "GBR"}, m.state.selected
    # ... and the choice survives a year change.
    m.set_year(2000)
    assert v.shown == "SWE"

    # Year change only moves the marker; the chart is not rebuilt.
    ax = v.figure.axes[0]
    m.set_year(2010)
    assert v.figure.axes[0] is ax
    assert list(v.year_line.get_xdata()) == [2010, 2010]

    # Deselecting the chosen country falls back to the remaining one.
    m.set_selected(["GBR"])
    assert v.shown == "GBR"

    t0 = time.perf_counter()
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        m.set_year(year)
        v.canvas.draw()
    per_frame = (time.perf_counter() - t0) / (YEAR_MAX - YEAR_MIN + 1) * 1000
    print(f"view: {per_frame:.0f} ms per animation frame (budget 250 ms)")
    assert per_frame < 250
    print("view: ok")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_view(load_table(sys.argv[1], sys.argv[2]))
    print("ALL TESTS PASSED")
