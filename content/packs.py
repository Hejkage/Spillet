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



# ============================================================================
# A PACK and a POOL OF PACKS - every setting they understand.
# Goes in content/packs.py.
#
#   the pack  knows WHICH monsters and HOW MANY of each
#   the area  knows WHICH packs may spawn and HOW MANY packs
# ============================================================================

register_pack(
    "frost_coven",                 # the name areas refer to
    [
        PackEntry(
            "frost_wraith",        # a key in enemy_configs
            count=(2, 4),          # how many of this monster, rolled per pack
            tier_offset=(0, 1),    # tier = area tier + this. None = the area's tier
            rank_weights=None,     # {"rare": 900} = this monster is nearly always rare
            extra=None,            # {"drop_tier": 10} etc, set straight on the enemy
        ),
        PackEntry("witch", count=(1, 2)),          # a second kind in the same pack
    ],
    spread=180,                    # how far from the spot its members stand. 0 = stacked
)

register_pack("lone_champion", [
    PackEntry("frost_wraith", count=(1, 1), tier_offset=(2, 3),
              rank_weights={"rare": 500, "epic": 200}), #Base weighting Normal: 1000 Uncommon: 250 rare: 80	epic: 20 legendary: 4, this just changes the individual weightings for each tier, not named = not changed
], spread=0)

register_pack("lone_champion2", [
    PackEntry("frost_wraith", count=(1, 1), tier_offset=(2, 3),
              rank_only={"rare": 5, "epic": 2}),  # rank only weighted ranks, can only be rare/epic in this example
], spread=0)

register_pack("loot_goblin", [
    PackEntry("frost_wraith", count=(1, 1), extra={"drop_tier": 10}),
], spread=0)

# A pool decides WHICH pack spawns at a spot. Weights work like drop weights.
frost_packs = PackPool([
    ("frost_coven",    5),
    ("lone_champion",  1),
    ("loot_goblin",    0.05),      # a rare treat
])