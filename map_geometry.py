"""Map geometry and country-code matching (owner: Shloka Kandukuri).

Shared component: turns the Natural Earth GeoJSON into one table keyed by the
same `iso3` codes as the shared data table, plus one Matplotlib PatchCollection
(one patch per country) that views can recolor with set_array().
"""
import geopandas as gpd
import numpy as np
from matplotlib.collections import PatchCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from shapely.geometry.polygon import orient

# Natural Earth ADM0_A3 codes that differ from OWID iso_code (NE -> OWID).
# Everything else matches directly. Run `report_unmatched` to see what is left.
NE_TO_OWID = {'SDS': 'SSD',   # South Sudan
              'PSX': 'PSE'}   # Palestine
# Natural Earth puts these island states in "Seven seas (open ocean)"
SEVEN_SEAS_FIX = {'MUS': 'Africa', 'SYC': 'Africa', 'MDV': 'Asia', 'SHN': 'Africa'}
DROP = {'ATA'}  # Antarctica: no data, wastes map space


def load_countries(map_file):
    """GeoDataFrame with columns iso3 (OWID code), name, continent, geometry."""
    world = gpd.read_file(map_file)
    world = world[~world['ADM0_A3'].isin(DROP)].copy()
    world['iso3'] = world['ADM0_A3'].replace(NE_TO_OWID)
    world['name'] = world['NAME']
    world['continent'] = world['CONTINENT']
    for code, cont in SEVEN_SEAS_FIX.items():
        world.loc[world['iso3'] == code, 'continent'] = cont
    return world[['iso3', 'name', 'continent', 'geometry']].reset_index(drop=True)


def report_unmatched(df_iso3, world):
    """Print countries in the data table with no shape (and vice versa)."""
    data = set(df_iso3)
    shapes = set(world['iso3'])
    no_shape = sorted(data - shapes)
    no_data = sorted(shapes - data)
    print(f'{len(data) - len(no_shape)} of {len(data)} data countries have a map shape')
    print('in data, no shape (map by hand or leave off):', no_shape)
    print('shape, no data (drawn grey):', len(no_data))
    return no_shape, no_data


def _geometry_to_path(geom):
    """Polygon/MultiPolygon -> one compound Path (holes kept via ring orientation)."""
    polys = geom.geoms if geom.geom_type == 'MultiPolygon' else [geom]
    paths = []
    for poly in polys:
        poly = orient(poly, 1.0)  # exterior CCW, holes CW
        for ring in [poly.exterior, *poly.interiors]:
            paths.append(Path(np.asarray(ring.coords)[:, :2], closed=True))
    return Path.make_compound_path(*paths)


def build_collection(world, **kwargs):
    """One PathPatch per row of `world`, in row order, so set_array(values) lines up."""
    patches = [PathPatch(_geometry_to_path(g)) for g in world.geometry]
    return PatchCollection(patches, **kwargs)