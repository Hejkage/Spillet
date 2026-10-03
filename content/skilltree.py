from systems.skilltree import register_skill_node, register_skill_edge, register_grant_label
from core.state import world

# What a grant is called in tooltips. Without a label here the tooltip falls
# back to the raw name ("dual_wield_two_handers" -> "Dual wield two handers").
register_grant_label("dual_wield_two_handers", "Can wield two two-handed weapons")
register_grant_label("ring_slots", "extra ring slot")
register_grant_label("pet_slots", "extra pet slot")

register_skill_node("start", "Origin", position=(800, 800), is_root=True)

register_skill_node("vitality_1", "Vitality I", position=(550, 600),
    stats=[{"stat": "max_health", "amount": 50, "type": "flat"}])
register_skill_node("vitality_2", "Vitality II", position=(550, 400),
    stats=[{"stat": "max_health", "amount": 50, "type": "flat"}])

register_skill_node("swiftness_1", "Swiftness I", position=(1050, 600),
    stats=[{"stat": "movement_speed", "amount": 20, "type": "flat"}])
register_skill_node("swiftness_2", "Swiftness II", position=(1050, 400),
    stats=[{"stat": "movement_speed", "amount": 20, "type": "flat"}])

register_skill_node("titans_grip", "Titans Grip", position=(550, 200),
    grants={"dual_wield_two_handers": True},
    description="You can equip 2 two-handed weapons")

register_skill_node("volley", "Volley", position=(1050, 100),
    mods=[("projectiles", 2),],     # projectile gems only (its tag)],
)

register_skill_node("chain_reaction", "Chain Reaction", position=(1050, 200),
    effects={
        "on_kill": [
            {"name": "explode", "radius": 1800, "damage": 50000},
        ],
    },
)

register_skill_edge("start", "vitality_1")
register_skill_edge("vitality_1", "vitality_2")
register_skill_edge("start", "swiftness_1")
register_skill_edge("swiftness_1", "swiftness_2")
register_skill_edge("vitality_2", "swiftness_2")
register_skill_edge("titans_grip", "swiftness_1")
register_skill_edge("titans_grip", "volley")
register_skill_edge("chain_reaction", "volley")


"""
# ============================================================================
# A SKILL TREE NODE - every setting it understands.
# Goes in content/skilltree.py. A node can do FOUR different things, and you
# can mix them freely on one node.
# ============================================================================
from systems.skilltree import register_skill_node, register_skill_edge
from core.state import world

# --- the entry point. is_root means it needs no allocated neighbour --------
register_skill_node("start", "Origin", position=(800, 800), is_root=True)


# ============================================================================
# 1. stats - plain stat mods. Same format as item mods.
#    Any stat registered with register_stat() in systems/items.py works, and
#    the stat panel and tooltips pick it up with no extra work.
# ============================================================================
register_skill_node(
    "vitality", "Vitality",
    position=(350, 300),                 # pixels on a 1600 x 1000 canvas
    stats=[
        {"stat": "max_health",   "type": "flat",      "amount": 50},
        {"stat": "max_health",   "type": "increased", "amount": 10},
        {"stat": "health_regen", "type": "flat",      "amount": 2},
    ],
    sprite_name=None,                    # optional icon instead of a circle
)


# ============================================================================
# 2. mods - named mechanics from systems/mods.py, applied to EVERY ability
#    the player uses. The same names a support gem or an always-on gem uses.
#
#    TAGS decide where each one lands, so one node behaves correctly on a
#    fireball and on a sword swing without any code here.
# ============================================================================
register_skill_node(
    "volley", "Volley",
    position=(1050, 100),
    mods=[
        ("projectiles", 2),              # projectile gems only (its tag)
    ],
)

register_skill_node(
    "wide_swings", "Wide Swings",
    position=(1450, 600),
    mods=[
        ("arc", 40),                     # melee gems only
        ("max_targets", 2),
        ("reach", 1.15),
    ],
)

register_skill_node(
    "brutality", "Brutality",
    position=(250, 400),
    mods=[
        ("damage", 1.15),                # anything that accepts "damage"
        ("crit_chance", 5),
    ],
    stats=[                              # mixing with stats is fine
        {"stat": "physical_damage", "type": "increased", "amount": 10},
    ],
)


# ============================================================================
# 3. grants - named permissions and counts that OTHER systems ask about.
#    Numbers add up across nodes; True counts as 1.
#
#    Nothing in the tree knows who listens. A system asks:
#        player.has_grant("dual_wield_two_handers")
#        player.grant_value("ring_slots")
#
#    An equip slot can be locked behind one, in content/items.py:
#        register_equip_slot("ring3", "main", accepts_slot_type("ring"),
#                            "inventory_slot_sprite", requires_grant="ring_slots")
# ============================================================================
register_skill_node(
    "third_ring", "Jeweller's Touch",
    position=(1600, 400),
    grants={
        "ring_slots": 1,                 # a number: two nodes give 2
    },
)

register_skill_node(
    "titan_grip", "Titan Grip",
    position=(1350, 200),
    grants={
        "dual_wield_two_handers": True,  # a flag
    },
)


# ============================================================================
# 4. effects - effect DATA, keyed by when it happens. The names are the ones
#    register_hit_effect / register_status use in systems/status.py, so the
#    SAME effect can be fired by a projectile, a melee swing, a pet, a
#    support gem or this node. Exactly the format a projectile carries:
#        effects=[{"name": "slow", "duration": 2.0, "amount": 0.4}]
#
#    "on_kill" is run from enemy_take_damage() in systems/enemies.py:
#        apply_hit_effects(self, player.effects_for("on_kill"))
#    A new event is that one line wherever it belongs; nothing here changes.
# ============================================================================
register_skill_node(
    "chain_reaction", "Chain Reaction",
    position=(1050, 200),
    effects={
        "on_kill": [
            {"name": "explode", "radius": 180, "damage": 40},
        ],
    },
)

register_skill_node(
    "bloodthirst", "Bloodthirst",
    position=(800, 200),
    effects={"on_kill": [{"name": "heal_caster", "percent": 2}]},
    stats=[{"stat": "lifesteal", "type": "flat", "amount": 2}],
    mods=[("damage", 1.05)],
    grants={"ring_slots": 1},            # all four on one node is allowed
)

# ============================================================================
# EDGES - two-way. A node can be allocated if AT LEAST ONE neighbour is.
# Loops and several routes to the same node work naturally.
# ============================================================================
register_skill_edge("start", "vitality")
register_skill_edge("start", "volley")
register_skill_edge("start", "brutality")
register_skill_edge("volley", "wide_swings")
register_skill_edge("vitality", "third_ring")
register_skill_edge("third_ring", "titan_grip")
register_skill_edge("brutality", "bloodthirst")
register_skill_edge("wide_swings", "chain_reaction")
"""