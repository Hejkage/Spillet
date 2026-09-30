from systems.areas import Area, register_area

def build_start(area):
    area.border("tree")
    area.line("tree", (50, 500), (2500, 500), spacing=100)

    area.add_enemy("baby_witch", 1000, 300)
    area.portal(2500, 300, "home", spawn=(500, 500))

register_area(Area("start", 2700, 2700, spawn=(350, 350), tile="grass_tile_sprite", build=build_start))