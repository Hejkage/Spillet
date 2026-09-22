"""The maps themselves: what each area contains and how it is built."""

from systems.world_objects import WorldObject
from systems.enemies import Enemy
from systems.areas import Area, Portal, register_area
from ui.chest import chest
from .shops import blacksmith, gemsmith

def build_forest(area):
    area.world_objects = [
        WorldObject(1800, 1400, "tree"),
        WorldObject(1800, 2000, "tree"),
    ]
    area.enemies = []
    area.enemies.extend(
        Enemy(x, 500, "witch") for x in range(50, 10000, 10)
    )

    area.portals = [
        Portal(1500, 1000, "home", target_spawn=(500, 500)),
    ]

def build_cave(area):
    area.world_objects = [
        WorldObject(700, 600, "tree"),
    ]
    area.enemies = [
        Enemy(800, 800, "slime_frog"),
        Enemy(1000, 600, "slime_frog"),
        Enemy(1500, 600, "slime_frog"),
        Enemy(0, 300, "slime_frog"),
        Enemy(90, 100, "slime_frog"),
    ]
    area.portals = [
        Portal(400, 300, "home", target_spawn=(500, 500)),
    ]

def build_home(area):
    trees = []

    spacing = 64
    margin = 40
    w, h = area.width, area.height

    x = margin
    while x <= w - margin:
        trees.append(WorldObject(x, margin, "tree"))
        trees.append(WorldObject(x, h - margin, "tree"))
        x += spacing

    y = margin
    while y <= h - margin:
        trees.append(WorldObject(margin, y, "tree"))
        trees.append(WorldObject(w - margin, y, "tree"))
        y += spacing

    area.world_objects = trees

    chest_obj = WorldObject(700, 500, "chest")
    chest_obj.linked_container = chest
    area.world_objects.append(chest_obj)

    shop_obj = WorldObject(900, 500, "shop")
    shop_obj.linked_container = blacksmith
    area.world_objects.append(shop_obj)

    shop_obj = WorldObject(1100, 500, "shop")
    shop_obj.linked_container = gemsmith
    area.world_objects.append(shop_obj)
   
    area.enemies = [Enemy(1600, 1500, "witch"),]
    area.portals = [
        Portal(400, 300, "forest", target_spawn=(1500, 1100)),
        Portal(400, 500, "cave", target_spawn=(400, 400)),
    ]

def build_start(area):
    trees = []

    spacing = 64
    margin = 40
    w, h = area.width, area.height

    x = margin
    while x <= w - margin:
        trees.append(WorldObject(x, margin, "tree"))
        trees.append(WorldObject(x, h - margin, "tree"))
        x += spacing

    y = margin
    while y <= h - margin:
        trees.append(WorldObject(margin, y, "tree"))
        trees.append(WorldObject(w - margin, y, "tree"))
        y += spacing

    area.world_objects = trees
    area.world_objects.extend(
        WorldObject(x, 500, "tree") for x in range(50, 10000, 100)
    )

    area.enemies = [Enemy(1000, 300, "baby_witch"),]
    area.portals = [Portal(2500, 300, "home", target_spawn=(500, 500)),]

register_area(Area("start", 2700, 2700, spawn=(350, 350), tile="grass_tile_sprite", build=build_start))
register_area(Area("forest", 30000, 30000, spawn=(1500, 1500), tile="grass_tile_sprite", build=build_forest))
register_area(Area("cave", 1600, 1600, spawn=(400, 400), tile="stone_tile_sprite", build=build_cave))
register_area(Area("home", 25000, 2500, spawn=(500, 500), tile="grass_tile_sprite", build=build_home))
