from systems.areas import Area, register_area
from ..packs import cave_packs

def build_cave(area):
    area.border("boulder", spacing=56)
    area.scatter_formations("cluster", "boulder", 4, count=4, radius=80)

    area.spawn_packs(cave_packs, count=2)

    area.portal(400, 300, "home", spawn=(500, 500))

register_area(Area("cave", 1600, 1600, spawn=(400, 400), tile="stone_tile_sprite", build=build_cave))