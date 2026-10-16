"""Gem tree LAYOUTS. Every gem item of that type gets its own points and sockets.
Node options: see systems/trees.py. Gem trees give "mods" (systems/mods.py)."""
from systems.gemtree import gem_tree
"""
tree = gem_tree("fireball")

tree.section("inferno", "Inferno")

tree.node("start",    "Ember Core",    position=(0, 0), is_root=True)
tree.node("dmg_1",    "Kindling",      position=(-200, 100),  connects="start",    mods=[("damage", 1.10)])
tree.node("aoe_1",    "Wide Blast",    position=(200, 100),   connects="start",    mods=[("aoe", 1.15)])
tree.node("crit_1",   "Searing Focus", position=(0, 100),     connects=["start", "dmg_2", "aoe_2"],    mods=[("crit_chance", 50)])
tree.node("dmg_2",    "Conflagration", position=(-100, 200),  connects="dmg_1",    mods=[("damage", 1.10)])
tree.node("aoe_2",    "Firestorm",     position=(100, 200),   connects="aoe_1",    mods=[("aoe", 1.25)])
tree.node("crit_2",   "Searing Focus", position=(200, 300),   connects="aoe_2",    mods=[("crit_chance", 100)])
tree.node("burn_1",   "Smoulder",      position=(0, 300),     connects=["dmg_2", "aoe_2"], max_points=5, per_point={"mods": [("burn_chance", 1)]})          # +1% burn chance per point
tree.node("socket_1", "Socket",        position=(100, 300),   connects="aoe_2", is_socket=True)
tree.node("socket_2", "Socket",        position=(-100, 300),  connects="dmg_2", is_socket=True)

tree.node("volley_or_pierce", "Volley or Pierce", position=(120, -300), connects="aoe_1", section="firestorm",
          kind="notable", choices=[{"name": "Volley",   "mods": [("projectiles", 1)]},
                                   {"name": "Piercing", "mods": [("pierce", 1)]}])
tree.node("big_one", "Big One", position=(-120, -300), connects="aoe_1", section="firestorm",
          kind="keystone", cost=3, mods=[("damage", 1.3)])
"""
# ------------------------------------------------------------------
# FIREBALL - three sections side by side
# ------------------------------------------------------------------
tree = gem_tree("fireball")

# --- Inferno: raw damage ----------------------------------------------
tree.section("inferno", "Inferno")
tree.node("inferno", "Inferno",                      position=(0, 0),        is_root=True,       section="inferno")
tree.node("dmg_1", "Kindling",                       position=(-100, 100),   connects="inferno", section="inferno", max_points=10, points_to_pass=5, per_point={"mods": [("increased_damage", 2)]})
tree.node("crit_chance_1", "Crit Chance I",          position=(0, 100),      connects="inferno", section="inferno", max_points=10, points_to_pass=5, per_point={"mods": [("crit_chance", 10)]})
tree.node("proj_speed_1", "Projectile Speed I",      position=(100, 100),    connects="inferno", section="inferno", max_points=10, points_to_pass=5, per_point={"mods": [("increased_projectile_speed", 5)]})
tree.node("dmg_2", "Conflagration",                  position=(-100, 200),   connects=["dmg_1", "crit_chance_1"],         one_way=True, section="inferno", mods=[("increased_damage", 15)])
tree.node("crit_chance_2", "Crit Chance II",         position=(100, 200),    connects=["crit_chance_1", "proj_speed_1"],  one_way=True, section="inferno", mods=[("crit_chance", 50)])
tree.node("socket_1", "Socket",                      position=(0, 200),      connects="crit_chance_1", one_way=True, section="inferno", kind="notable", cost=5, is_socket=True)
tree.node("crit_dmg_1", "Crit Damage I",             position=(200, 300),    connects="crit_chance_2", one_way=True, section="inferno", max_points=5, per_point={"mods": [("crit_damage", 2)]})
tree.node("flat_fire", "Flat Fire I",                position=(100, 300),    connects="crit_chance_2", one_way=True, section="inferno", max_points=5, per_point={"mods": [("added_fire", 2)]})
tree.node("inc_ele_dmg_1", "Elemental Damage",       position=(0, 300),      connects=["crit_chance_2", "dmg_2"], one_way=True, section="inferno", max_points=5, per_point={"mods": [("increased_elemental", 3)]})
tree.node("burn_1", "Smoulder",                      position=(-100, 300),   connects="dmg_2", one_way=True, section="inferno", max_points=5, per_point={"mods": [("burn_chance", 1)]})
tree.node("hybrid_crit", "Hybrid Crit",              position=(-200, 300),   connects="dmg_2", one_way=True, section="inferno", max_points=5, per_point={"mods": [("crit_chance", 5), ("crit_damage", 1)]})
tree.node("proj_pierce", "Multi Choice",             position=(-100, 400),   connects="burn_1", one_way=True, section="inferno", kind="notable", choices=[{"name": "Volley", "mods": [("projectiles", 1)]}, {"name": "Piercing", "mods": [("pierce", 1)]}])
tree.node("proj_explode", "Smoulder",                position=(100, 400),    connects="flat_fire", one_way=True, section="inferno", kind="notable", choices=[{"name": "Volley", "mods": [("projectiles", 1)]}, {"name": "Exploding", "mods": [("explode_on_hit", 50)]}])

# --- Firestorm: area and projectiles ----------------------------------
tree.section("firestorm", "Firestorm")
tree.node("firestorm", "Firestorm", position=(-500, 0), is_root=True, section="firestorm")
tree.node("aoe_1", "Wide Blast", position=(0, -150), connects="firestorm", section="firestorm", max_points=10, per_point={"mods": [("aoe", 1.02)]})
tree.node("proj_1", "Split Flame", position=(0, -300), connects="aoe_1", one_way=True, section="firestorm", kind="notable", mods=[("projectiles", 1)])

# --- Embers: burning and crits ----------------------------------------
tree.section("embers", "Embers")
tree.node("embers", "Embers", position=(500, 0), is_root=True, section="embers")
tree.node("burn_10", "Smoulder", position=(400, -150), connects="embers", section="embers", max_points=10, per_point={"mods": [("burn_chance", 1)]})          # +1% burn chance per point
tree.node("crit_1", "Searing Focus", position=(400, -300), connects="burn_10", one_way=True, section="embers", kind="notable", mods=[("crit_chance", 80)])
tree.node("socket_2", "Socket", position=(520, -150), connects="embers", section="embers", is_socket=True)

# ------------------------------------------------------------------
# SHOTGUN BLAST - no sections: one root, always open
# ------------------------------------------------------------------
tree = gem_tree("shotgun_blast")
tree.node("start", "Test socket", position=(0, 0), is_root=True)
tree.node("dmg_1", "Kindling",    position=(-200, -180), connects="start", is_socket=True)
