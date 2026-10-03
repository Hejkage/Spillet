# ============================================================================
# AN AREA - every setting it understands.
# One file per area in content/areas/. Loaded automatically.
# ============================================================================
from systems.areas import Area, register_area
from ..packs import frost_packs
# from ui.chest import chest
# from ..shops import blacksmith

def build_frost_cavern(area):
    # --- keep ground free BEFORE you build, or it only stops new scenery ----
    area.reserve(2500, 2500, 400)          # x, y, radius. A boss arena, say.
    # The spawn point and every portal reserve themselves automatically.

    # --- a wall round the edge ----------------------------------------------
    area.border("boulder", spacing=56, margin=40)   # follows the map size

    # --- a straight row ------------------------------------------------------
    area.line("tree", (200, 900), (4800, 900), spacing=100)

    # --- formations: cluster / ring / vein / clump ---------------------------
    # amount = how many copies of the shape. The rest go to the shape itself.
    area.scatter_formations("clump",   "tree",    12, count=14, radius=260, tightness=2.0)
    area.scatter_formations("cluster", "boulder", 18, count=6,  radius=110)
    area.scatter_formations("ring",    "boulder", 3,  count=10, radius=200, jitter=20)
    area.scatter_formations("vein",    "boulder", 6,  count=8,  step=70, jitter=35, bounds=(1000, 1000, 4000, 4000), gap=300)

    # --- loose single objects -------------------------------------------------
    area.scatter("boulder", 20, bounds=None, gap=80)

    # --- things you place by hand (never removed by a reservation) -----------
    # area.add("chest", 700, 500, container=chest)
    # area.add("shop",  900, 500, container=blacksmith)

    # --- monsters -------------------------------------------------------------
    area.spawn_packs(
        frost_packs,          # a PackPool, or just ["frost_coven", "loot_goblin"]
        count=(8, 14),        # HOW MANY PACKS. a number, or (min, max)
        spots=None,           # your own [(x, y), ...]; None = find open ground
        picker="random",      # how spots are chosen, see systems/packs.py
        gap=250,              # clear room each pack spot needs
    )
    area.add_enemy("frost_wraith", 2500, 2500)     # one exact monster

    # --- the way out ----------------------------------------------------------
    area.portal(400, 300, "home", spawn=(500, 500))   # x, y, target area, arrival spot

register_area(Area(
    "frost_cavern",                  # the name portals use
    5000, 5000,                      # width, height in world pixels
    spawn=(350, 350),                # where the player appears
    tier=7,                          # 1-10. Monster stats and loot quality
    persistent=False,                # False = rebuilt on every entry, ground wiped
                                     # True  = kills and drops stay until restart
    tile="stone_tile_sprite",        # the ground texture
    build=build_frost_cavern,
))