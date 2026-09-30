"""Monster packs: which enemies spawn together, and how many.

Pure data. Built like drop groups - see content/drops.py.
"""

from systems.packs import PackEntry, PackPool, register_pack

register_pack("witch_coven", [
    PackEntry("witch", count=(5, 9)),
])

register_pack("lone_witch", [
    PackEntry("witch", count=(1, 1)),
], spread=0)

register_pack("slime_nest", [
    PackEntry("slime_frog", count=(3, 6)),
], spread=180)

register_pack("mixed_camp", [
    PackEntry("witch", count=(1, 2)),
    PackEntry("slime_frog", count=(2, 4)),
], spread=200)

# A pool decides WHICH pack spawns at a spot. Weights work like drop weights.
forest_packs = PackPool([
    ("witch_coven", 5),
    ("mixed_camp",  1),
])

cave_packs = PackPool([
    ("slime_nest", 5),
    ("mixed_camp", 1),
])