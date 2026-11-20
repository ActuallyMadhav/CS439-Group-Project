"""Tests for the selection model and view B (owner: Madhav Anantharam).

Run headless:
    QT_QPA_PLATFORM=offscreen python tests/test_part_b.py <owid-co2-data.csv> <ne_50m.geojson>
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
from views.bubble_view import BubblePanel


def test_model():
    m = SelectionModel()
    seen = []
    m.changed.connect(seen.append)

    m.set_year(2000)
    m.set_year(2000)                       # no change -> no signal
    assert len(seen) == 1 and seen[-1].year == 2000
    m.set_year(1900)
    assert m.state.year == YEAR_MIN        # clamped
    m.set_year(2100)
    assert m.state.year == YEAR_MAX
    m.toggle("GBR"); m.toggle("SWE"); m.toggle("GBR")
    assert m.state.selected == {"SWE"}
    m.add_selected(["USA", "CHN"])
    assert m.state.selected == {"SWE", "USA", "CHN"}
    m.set_basis("consumption")
    try:
        m.set_basis("bogus")
        raise AssertionError("invalid basis accepted")
    except ValueError:
        pass
    m.set_continent("Europe")
    m.reset()
    s = m.state
    assert (s.year, s.basis, s.continent, s.selected) == (YEAR_MAX, "territorial", None, frozenset())
    print("model: ok")


def _press(view, x, y, name="button_press_event", key=None):
    px, py = view.ax.transData.transform((x, y))
    button = None if name == "motion_notify_event" else 1
    return MouseEvent(name, view.canvas, px, py, button=button, key=key)


def test_view(df):
    m = SelectionModel()
    v = BubblePanel(m)
    v.resize(1200, 760)
    v.canvas.resize(1200, 760)
    v.draw(df)
    n = len(v.iso)
    print(f"view: {n} countries drawn")
    assert n >= 160

    # Year change moves bubbles: count visible points per basis.
    m.set_year(2022)
    terr = int(v._cur["valid"].sum())
    m.set_basis("consumption")
    cons = int(v._cur["valid"].sum())
    print(f"view: 2022 visible bubbles territorial={terr}, consumption={cons}")
    assert cons < terr

    # Click on the UK's bubble toggles it into the selection.
    i = int(np.flatnonzero(v.iso == "GBR")[0])
    ev = _press(v, v._cur["x"][i], v._cur["y_plot"][i])
    v._on_select(ev, _press(v, v._cur["x"][i], v._cur["y_plot"][i], "button_release_event"))
    assert m.state.selected == {"GBR"}, m.state.selected
    # Click on empty space clears it.
    v._on_select(_press(v, 400, 60), _press(v, 400, 60, "button_release_event"))
    assert m.state.selected == frozenset()

    # Brush the rich, high-emission corner: should select only countries inside the box.
    m.set_basis("territorial")
    v._on_select(_press(v, 30_000, 8), _press(v, 150_000, 40, "button_release_event"))
    picked = m.state.selected
    c = v._cur
    for code in picked:
        k = int(np.flatnonzero(v.iso == code)[0])
        assert 30_000 <= c["x"][k] <= 150_000 and 8 <= c["y_plot"][k] <= 40
    print(f"view: brush picked {len(picked)} countries, e.g. {sorted(picked)[:6]}")
    assert {"USA", "AUS"} <= picked

    # Shift+brush adds to the selection.
    before = set(picked)
    v._on_select(_press(v, 1000, 0.05, key="shift"), _press(v, 3000, 0.3, "button_release_event"))
    assert before < m.state.selected

    # Continent filter: brushing ignores countries outside the continent.
    m.set_continent("Europe")
    v._on_select(_press(v, 310, 0.021), _press(v, 190_000, 95, "button_release_event"))
    conts = {v.cont[int(np.flatnonzero(v.iso == c)[0])] for c in m.state.selected}
    assert conts == {"Europe"}, conts
    m.set_continent(None)

    # Trails: one line per selected country.
    m.set_selected(["GBR", "SWE", "CHN"])
    assert len(v.trails.get_segments()) == 3

    # Hover: tooltip ring + text appear on the UK's bubble (HW3 HoverTooltip).
    m.set_year(2022)
    v.canvas.draw()
    i = int(np.flatnonzero(v.iso == "GBR")[0])
    v.tooltip._on_motion(_press(v, v._cur["x"][i], v._cur["y_plot"][i], "motion_notify_event"))
    assert v.tooltip.annotation.get_visible()
    assert "United Kingdom" in v.tooltip.annotation.get_text(), v.tooltip.annotation.get_text()
    print("view: tooltip ->", v.tooltip.annotation.get_text().splitlines()[0])

    # Off-scale value: Kuwait 1991 is pinned to the top edge, not dropped.
    m.set_year(1991)
    k = int(np.flatnonzero(v.iso == "KWT")[0])
    assert v._cur["capped"][k] and v._cur["valid"][k]

    # Animation speed: time one full 1990-2022 play-through (update + full redraw).
    m.set_selected(["GBR", "SWE", "USA", "CHN", "IND"])
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
    test_model()
    test_view(load_table(sys.argv[1], sys.argv[2]))
    print("ALL TESTS PASSED")
