"""Shared tooltip and highlight style for every view (owner: Tanisha Phadke).

One look for details-on-demand and for selection highlighting across views A-E:

    from tooltip import HoverTooltip, country_text, CONTINENT_COLORS, EXCLUDED_COLOR

Highlight style (proposal: "common tooltip and highlight style used by every view")
    CONTINENT_COLORS   category colors (HW1 dictionary, Okabe-Ito palette)
    EXCLUDED_COLOR     grey for countries outside the selection / continent (HW2)
    SELECTED_EDGE, SELECTED_LW, UNSELECTED_LW   outline of selected marks
    HOVER_COLOR        ring drawn around the hovered mark

HoverTooltip (HW3 tooltip, generalised)
    - the box and ring are animated artists blitted over a cached background,
      so hovering never triggers a full redraw (HW3 on_draw / update_overlay);
    - the box flips towards the centre of the axes so it is never clipped (HW3);
    - hit testing happens in pixels via transData, so log axes work too.

    Two ways to say what can be hovered:
      points:  tip = HoverTooltip(fig, ax, text_fn)
               tip.set_data(xy, areas, ids)        # call after every update
               -> text_fn(ids[k]) is shown for the nearest point under the mouse
      custom:  tip = HoverTooltip(fig, ax, text_fn, hit_fn=my_hit)
               my_hit(event) -> (key, anchor_xy, ring_area or None) or None
               -> text_fn(key) is shown at anchor_xy (map patches, lines, ...)

country_text(...) builds the standard country box (name, year, both emission
measures, GDP per person, population), with labels aligned like HW3 field().
"""
import numpy as np

# ---- highlight style -----------------------------------------------------------
CONTINENT_COLORS = {'Africa': '#E69F00', 'Asia': '#D55E00', 'Europe': '#0072B2',
                    'North America': '#CC79A7', 'South America': '#009E73',
                    'Oceania': '#56B4E9'}
EXCLUDED_COLOR = (0.75, 0.75, 0.75)   # HW2
SELECTED_EDGE = 'black'
SELECTED_LW = 1.6
UNSELECTED_LW = 0.5
HOVER_COLOR = 'red'

MIN_HOVER_RADIUS_PX = 5    # HW3
LABEL_WIDTH = 14           # HW3 field() alignment


def rgb(hex_color):
    h = hex_color.lstrip('#')
    return tuple(int(h[k:k + 2], 16) / 255 for k in (0, 2, 4))


# ---- tooltip text ----------------------------------------------------------------
def field(label, value):   # HW3
    return f'{label + ":":<{LABEL_WIDTH}}{value}'


def _fmt(value, fmt, missing='no data'):
    return fmt.format(value) if value is not None and np.isfinite(value) else missing


def country_text(name, year, continent=None, terr_pc=np.nan, cons_pc=np.nan,
                 gdp_pc=np.nan, population=np.nan, extra=()):
    """Standard details-on-demand box shared by all views."""
    lines = [field('Country', f'{name} ({year})')]
    if continent:
        lines.append(field('Continent', continent))
    lines += [field('GDP/person', _fmt(gdp_pc, '${:,.0f}')),
              field('Territorial', _fmt(terr_pc, '{:.1f} t CO₂/person')),
              field('Consumption', _fmt(cons_pc, '{:.1f} t CO₂/person', 'no estimate')),
              field('Population', _fmt(population / 1e6 if population is not None else np.nan,
                                       '{:,.1f} million'))]
    lines += [field(label, value) for label, value in extra]
    return '\n'.join(lines)


# ---- hit testing -------------------------------------------------------------------
def points_hit(ax, fig, xy, areas, px, py, min_radius=MIN_HOVER_RADIUS_PX):
    """Index of the nearest point (scatter area in points^2) under pixel (px, py), or None."""
    if len(xy) == 0:
        return None
    pts = ax.transData.transform(xy)   # works for log axes too
    dist = np.hypot(pts[:, 0] - px, pts[:, 1] - py)
    radius = np.sqrt(np.asarray(areas, float) / np.pi) * fig.dpi / 72.0
    within = dist <= np.maximum(radius, min_radius)
    if not within.any():
        return None
    return int(np.argmin(np.where(within, dist, np.inf)))


# ---- the tooltip ---------------------------------------------------------------------
class HoverTooltip:   # HW3

    def __init__(self, fig, ax, node_text, hit_fn=None):
        self.fig, self.ax, self.canvas = fig, ax, fig.canvas
        self.node_text = node_text
        self.hit_fn = hit_fn
        self.background = None
        self.current = None

        self.annotation = ax.annotate(
            '', xy=(0, 0), xytext=(15, 15), textcoords='offset points',
            fontsize=8, family='monospace', multialignment='left', zorder=10, annotation_clip=False,
            bbox=dict(boxstyle='round', fc='white', ec='black', alpha=0.92),
            visible=False, animated=True)
        self.node_ring = ax.scatter([], [], s=[], facecolors='none', edgecolors=HOVER_COLOR,
                                    linewidths=2, zorder=9, visible=False, animated=True)
        self.artists = (self.node_ring, self.annotation)
        self.set_data(np.empty((0, 2)), np.empty(0), np.empty(0, int))

        self.canvas.mpl_connect('draw_event', self._on_draw)
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.canvas.mpl_connect('figure_leave_event', lambda e: self._show(None))

    def set_data(self, node_xy, node_area, node_ids):
        """Set what can currently be hovered (points mode: only visible, pickable marks)."""
        self.node_xy = np.asarray(node_xy, float).reshape(-1, 2)
        self.node_area = np.asarray(node_area, float)
        self.node_ids = np.asarray(node_ids)
        self.hide()

    def hide(self):
        self.current = None
        for artist in self.artists:
            artist.set_visible(False)

    # blitting helpers (HW3)
    def _on_draw(self, event):
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)
        for artist in self.artists:
            if artist.get_visible():
                self.ax.draw_artist(artist)

    def _blit(self):
        if self.background is None:
            self.canvas.draw_idle()
            return
        self.canvas.restore_region(self.background)
        for artist in self.artists:
            if artist.get_visible():
                self.ax.draw_artist(artist)
        self.canvas.blit(self.fig.bbox)

    # picking
    def hit(self, px, py):
        """Index (into node_ids) of the nearest point under pixel (px, py), or None."""
        return points_hit(self.ax, self.fig, self.node_xy, self.node_area, px, py)

    def find(self, event):
        """(key, anchor_xy, ring_area) for whatever is under the mouse, or None."""
        if self.hit_fn is not None:
            return self.hit_fn(event)
        k = self.hit(event.x, event.y)
        if k is None:
            return None
        return self.node_ids[k], self.node_xy[k], max(self.node_area[k] * 1.6, 60)

    def _on_motion(self, event):
        if event.inaxes is not self.ax or event.button is not None:
            self._show(None)
            return
        self._show(self.find(event))

    def _show(self, found):
        key = None if found is None else found[0]
        if key == self.current:
            return
        self.hide()
        if found is not None:
            key, xy, ring_area = found
            self.current = key
            if ring_area is not None:
                self.node_ring.set_offsets([xy])
                self.node_ring.set_sizes([ring_area])
                self.node_ring.set_visible(True)

            # keep the box inside the axes: flip it towards the centre (HW3)
            bbox = self.ax.bbox
            px, py = self.ax.transData.transform(xy)
            right = px > bbox.x0 + bbox.width * 0.5
            top = py > bbox.y0 + bbox.height * 0.5
            self.annotation.xy = tuple(xy)
            self.annotation.set_text(self.node_text(key))
            self.annotation.set_position((-15 if right else 15, -15 if top else 15))
            self.annotation.set_horizontalalignment('right' if right else 'left')
            self.annotation.set_verticalalignment('top' if top else 'bottom')
            self.annotation.set_visible(True)
        self._blit()
