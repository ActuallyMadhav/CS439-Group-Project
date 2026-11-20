"""Tests for view A click-to-select and the A -> B link (milestone 2).

Run headless:
    QT_QPA_PLATFORM=offscreen python tests/test_part_a.py <owid-co2-data.csv> <ne_50m.geojson>
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from matplotlib.backend_bases import MouseEvent
from PyQt5.QtWidgets import QApplication

from data import load_table
from selection import SelectionModel
from tooltip import EXCLUDED_COLOR
from views.bubble_view import BubblePanel
from views.map_view import MapPanel


def _click(view, lon, lat):
    px, py = view.ax.transData.transform((lon, lat))
    event = MouseEvent("button_press_event", view.canvas, px, py, button=1)
    view._on_click(event)


def test_map(df, map_file):
    m = SelectionModel()
    a = MapPanel(m, map_file)
    a.resize(1100, 550)
    a.canvas.resize(1100, 550)
    a.draw(df)
    b = BubblePanel(m)
    b.resize(1200, 760)
    b.canvas.resize(1200, 760)
    b.draw(df)
    a.canvas.draw()

    # Click on England selects the UK; clicking it again removes it.
    _click(a, -1.5, 52.5)
    assert m.state.selected == {"GBR"}, m.state.selected
    _click(a, 2.5, 46.5)                       # France
    assert m.state.selected == {"GBR", "FRA"}, m.state.selected
    _click(a, 2.5, 46.5)
    assert m.state.selected == {"GBR"}

    # Selected countries get the dark outline on the map.
    i = int(np.flatnonzero(a.world["iso3"] == "GBR")[0])
    assert a.collection.get_linewidths()[i] > 1.0

    # ... and in view B the UK keeps its color while every other bubble turns grey.
    faces = b.bubbles.get_facecolors()
    grey = np.all(np.isclose(faces[:, :3], EXCLUDED_COLOR), axis=1)
    k = int(np.flatnonzero(b.iso == "GBR")[0])
    assert not grey[k] and grey.sum() == len(b.iso) - 1
    print("map: click on GBR selects it and view B highlights it")

    # Continent filter: countries outside it cannot be picked; a click there clears.
    m.set_continent("Asia")
    _click(a, 2.5, 46.5)
    assert m.state.selected == frozenset()
    m.set_continent(None)

    # Click on the ocean clears the selection.
    m.set_selected(["GBR", "USA"])
    _click(a, -30, 0)
    assert m.state.selected == frozenset()
    print("map: ok")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_map(load_table(sys.argv[1], sys.argv[2]), sys.argv[2])
    print("ALL TESTS PASSED")
