from systems.areas import Area, register_area
from ui.chest import chest
from ..shops import blacksmith, gemsmith

def build_home(area):
    area.border("tree")

    area.add("chest", 700, 500, container=chest)
    area.add("shop",  900, 500, container=blacksmith)
    area.add("shop", 1100, 500, container=gemsmith)

    area.add_enemy("witch", 1600, 1500)

    area.portal(400, 300, "forest", spawn=(1500, 1100))
    area.portal(400, 500, "cave",   spawn=(400, 400))

register_area(Area("home", 25000, 2500, spawn=(500, 500), tile="grass_tile_sprite", build=build_home))