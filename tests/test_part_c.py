"""Tests for view C, the decoupling chart (owner: Shivam Rastogi).

Run headless:
    QT_QPA_PLATFORM=offscreen python tests/test_part_c.py <owid-co2-data.csv> <ne_50m.geojson>
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from matplotlib.backend_bases import MouseEvent
from PyQt5.QtWidgets import QApplication

from data_minimal import load_table
from metrics import add_metrics
from selection import SelectionModel, YEAR_MAX, YEAR_MIN
from views.decoupling_view import DEFAULT_COUNTRIES, MAX_PANELS, DecouplingPanel, runs


def names_shown(v):
    return [v.names[p['row']] for p in v.panels]


def test_runs():
    assert runs([0, 1, 1, 0, 1]) == [(1, 2), (4, 4)]
    assert runs([1, 1]) == [(0, 1)]
    assert runs([0, 0]) == []


def test_view(df):
    m = SelectionModel()
    v = DecouplingPanel(m)
    v.resize(1200, 760)
    v.canvas.resize(1200, 760)
    v.update_view(m.state)          # before draw(): must not crash
    v.draw(df)

    # nothing selected -> the default example countries
    assert [v.iso[p['row']] for p in v.panels] == [c for c in DEFAULT_COUNTRIES]
    assert 'Nothing selected' in v.note_text.get_text()

    # selection drives the panels, most populous first
    m.set_selected(['SWE', 'GBR'])
    assert names_shown(v) == ['United Kingdom', 'Sweden'], names_shown(v)

    # more than MAX_PANELS -> capped, with a note
    m.set_selected(['GBR', 'SWE', 'USA', 'CHN', 'IND', 'FRA'])
    assert len(v.panels) == MAX_PANELS
    assert names_shown(v)[:2] == ['India', 'China']
    assert '+2 more' in v.note_text.get_text()

    # continent filter with nothing selected -> that continent's largest economies
    m.clear_selection()
    m.set_continent('Europe')
    assert all(v.cont[p['row']] == 'Europe' for p in v.panels)
    m.set_continent(None)

    # basis toggle rebuilds the panels and moves the shading
    m.set_selected(['GBR'])
    m.set_year(2008)
    ax = v.panels[0]['ax']
    terr_spans = len(ax.patches)
    terr_text = v.panels[0]['change'].get_text()
    m.set_basis('consumption')
    ax = v.panels[0]['ax']
    cons_spans = len(ax.patches)
    cons_text = v.panels[0]['change'].get_text()
    print(f'view: UK 2008 territorial -> {terr_text!r}')
    print(f'view: UK 2008 consumption -> {cons_text!r}')
    assert '(decoupled)' in terr_text and '(not decoupled)' in cons_text
    assert terr_spans >= 1 and cons_spans >= 1

    # year marker follows the slider without rebuilding the axes
    m.set_year(2015)
    assert v.panels[0]['ax'] is ax
    assert v.panels[0]['year_line'].get_xdata()[0] == 2015

    # hover shows a tooltip for the nearest year
    v.canvas.draw()
    px, py = ax.transData.transform((2010.2, 120))
    v._on_motion(MouseEvent('motion_notify_event', v.canvas, px, py))
    tip = v.panels[0]['tip']
    assert tip.get_visible()
    assert tip.get_text().startswith('United Kingdom (2010)'), tip.get_text()
    print('view: tooltip ->', tip.get_text().splitlines()[0])

    # a country with no 1990 baseline is explained, not silently dropped
    no_base = [c for c in v.iso if not v.has_base[v.row[c]]]
    if no_base:
        m.set_selected(['GBR', no_base[0]])
        assert 'No 1990' in v.note_text.get_text()

    # play speed: one full 1990-2022 run with 4 panels
    m.set_selected(['GBR', 'SWE', 'USA', 'CHN'])
    t0 = time.perf_counter()
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        m.set_year(year)
        v.canvas.draw()
    per_frame = (time.perf_counter() - t0) / (YEAR_MAX - YEAR_MIN + 1) * 1000
    print(f'view: {per_frame:.0f} ms per animation frame (budget 250 ms)')
    assert per_frame < 250
    print('view: ok')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    test_runs()
    test_view(add_metrics(load_table(sys.argv[1], sys.argv[2])))
    print('ALL VIEW C TESTS PASSED')
