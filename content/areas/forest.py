from systems.areas import Area, register_area
from ..packs import forest_packs

def build_forest(area):
    area.border("tree")

    area.scatter_formations("clump",   "tree",    12)
    area.scatter_formations("cluster", "boulder", 18)
    area.scatter_formations("vein",    "boulder", 6)

    area.spawn_packs(forest_packs, count=(12, 18))

    area.portal(1500, 1000, "home", spawn=(500, 500))

register_area(Area("forest", 5000, 5000, spawn=(200, 200),
                   level=54, persistent=True,
                   tile="grass_tile_sprite", build=build_forest))