"""Tests for the shared tooltip and view D (owner: Tanisha Phadke).

Run headless:
    QT_QPA_PLATFORM=offscreen python tests/test_part_d.py <owid-co2-data.csv> <ne_50m.geojson>
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from matplotlib.backend_bases import MouseEvent
from PyQt5.QtWidgets import QApplication

from data import load_table
from selection import SelectionModel, YEAR_MAX, YEAR_MIN
from tooltip import EXCLUDED_COLOR, country_text, field
from views.outsourcing_view import OutsourcingPanel


def test_text():
    text = country_text("Sweden", 2022, "Europe", 3.6, 6.4, 55_000, 10.5e6,
                        extra=[("Net imported", "+2.8 t/person")])
    lines = text.splitlines()
    assert lines[0] == field("Country", "Sweden (2022)")
    assert all(line[13] == " " for line in lines)          # values line up (HW3 field)
    assert "no estimate" in country_text("Chad", 2022, "Africa", 0.1, np.nan, 1500, 18e6)
    print("text: ok")


def _event(view, x, y, name="motion_notify_event"):
    px, py = view.ax.transData.transform((x, y))
    button = None if name == "motion_notify_event" else 1
    return MouseEvent(name, view.canvas, px, py, button=button)


def _row(view, code):
    return int(np.flatnonzero(view.iso == code)[0])


def test_view(df):
    m = SelectionModel()
    v = OutsourcingPanel(m)
    v.resize(1000, 800)
    v.canvas.resize(1000, 800)
    v.draw(df)
    n = len(v.iso)
    print(f"view: {n} countries with a consumption estimate")
    assert 110 <= n <= 130
    assert "OWID_WRL" not in v.iso

    # 2022: the UK consumes more than it emits (above the diagonal), China the reverse.
    m.set_year(2022)
    gbr, chn = _row(v, "GBR"), _row(v, "CHN")
    assert v._cur["y"][gbr] > v._cur["x"][gbr], "UK should be a net importer"
    assert v._cur["y"][chn] < v._cur["x"][chn], "China should be a net exporter"

    # Year change moves the points.
    before = v._cur["x"][gbr]
    m.set_year(1990)
    assert v._cur["x"][gbr] != before

    # Selection: unselected points turn grey, selected keep their color and get a label.
    m.set_year(2022)
    m.set_selected(["GBR", "CHN"])
    faces = v.points.get_facecolors()
    grey = np.all(np.isclose(faces[:, :3], EXCLUDED_COLOR), axis=1)
    assert grey.sum() == int(v._cur["valid"].sum()) - 2, grey.sum()
    assert sorted(t.get_text() for t in v.labels) == ["China", "United Kingdom"]

    # Continent filter: countries outside it cannot be hovered.
    m.set_continent("Asia")
    assert not v._cur["pickable"][gbr] and v._cur["pickable"][chn]
    m.set_continent(None)

    # Hover: the shared tooltip shows the UK with both measures and the net import.
    v.canvas.draw()
    v.tooltip._on_motion(_event(v, v._cur["x_plot"][gbr], v._cur["y_plot"][gbr]))
    text = v.tooltip.annotation.get_text()
    assert v.tooltip.annotation.get_visible()
    assert "United Kingdom" in text and "Net imported" in text and "net importer" in text, text
    print("view: tooltip ->", text.splitlines()[0], "|", text.splitlines()[-1].strip())
    # moving off the point hides it again
    v.tooltip._on_motion(_event(v, 0.03, 60))
    assert not v.tooltip.annotation.get_visible()

    # Off-scale value: Kuwait 1991 is pinned to the edge, not dropped.
    m.set_year(1991)
    k = _row(v, "KWT")
    assert v._cur["capped"][k] and v._cur["valid"][k]

    # Animation speed, same budget as view B.
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
    test_text()
    test_view(load_table(sys.argv[1], sys.argv[2]))
    print("ALL TESTS PASSED")