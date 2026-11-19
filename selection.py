"""Shared selection model for the CO2 project (owner: Madhav Anantharam).

Every view reads the current state from one SelectionModel and changes it only
through the setters below. Views never talk to each other directly: a view that
wants to select countries calls a setter, the model emits `changed`, and every
view (including the one that made the change) redraws from the new state.

The contract for team members writing a view:

    class MyView(BaseView):
        def draw(self, df):        # called once at start-up with the tidy table
            ...
        def update_view(self, state):   # called on every state change
            ...

    model.changed.connect(my_view.update_view)

State fields
    year       int, 1990..2022 (GDP ends in 2022, consumption CO2 starts in 1990)
    basis      "territorial" or "consumption"
    continent  None (all) or one continent name
    selected   frozenset of ISO-3 codes, e.g. frozenset({"GBR", "SWE"})
"""

from dataclasses import dataclass, replace, field

from PyQt5.QtCore import QObject, pyqtSignal

YEAR_MIN = 1990
YEAR_MAX = 2022
BASES = ("territorial", "consumption")
CONTINENTS = ("Africa", "Asia", "Europe", "North America", "South America", "Oceania")


@dataclass(frozen=True)
class SelectionState:
    year: int = YEAR_MAX
    basis: str = "territorial"
    continent: str = None
    selected: frozenset = field(default_factory=frozenset)


class SelectionModel(QObject):
    """Holds the shared state and emits `changed(state)` only when it really changes."""

    changed = pyqtSignal(object)

    def __init__(self, state=None):
        super().__init__()
        self._state = state or SelectionState()

    @property
    def state(self):
        return self._state

    # ---- setters -------------------------------------------------------------
    def set_year(self, year):
        year = max(YEAR_MIN, min(YEAR_MAX, int(year)))
        self._apply(year=year)

    def set_basis(self, basis):
        if basis not in BASES:
            raise ValueError(f"basis must be one of {BASES}, got {basis!r}")
        self._apply(basis=basis)

    def set_continent(self, continent):
        if continent is not None and continent not in CONTINENTS:
            raise ValueError(f"unknown continent {continent!r}")
        self._apply(continent=continent)

    def set_selected(self, iso3_codes):
        self._apply(selected=frozenset(iso3_codes))

    def add_selected(self, iso3_codes):
        self._apply(selected=self._state.selected | frozenset(iso3_codes))

    def toggle(self, iso3):
        sel = set(self._state.selected)
        sel.symmetric_difference_update({iso3})
        self._apply(selected=frozenset(sel))

    def clear_selection(self):
        self._apply(selected=frozenset())

    def reset(self):
        self._apply(year=YEAR_MAX, basis="territorial", continent=None, selected=frozenset())

    # ---- internals -----------------------------------------------------------
    def _apply(self, **changes):
        new = replace(self._state, **changes)
        if new != self._state:
            self._state = new
            self.changed.emit(new)


class BaseView:
    """Interface every view implements. Views only read state and call model setters."""

    def __init__(self, model=None, **_qt_kwargs):
        # A view that is also a QWidget (class MyView(QtWidgets.QWidget, BaseView))
        # gets this called once by PyQt with no model; call it yourself with the model.
        if model is None:
            return
        self.model = model
        model.changed.connect(self.update_view)

    def draw(self, df):
        raise NotImplementedError

    def update_view(self, state):
        raise NotImplementedError
