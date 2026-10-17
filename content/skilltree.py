from systems.skilltree import register_skill_node, register_skill_edge, register_grant_label
from core.state import world

# What a grant is called in tooltips. Without a label here the tooltip falls
# back to the raw name ("dual_wield_two_handers" -> "Dual wield two handers").
register_grant_label("dual_wield_two_handers", "Can wield two two-handed weapons")
register_grant_label("ring_slots", "extra ring slot")
register_grant_label("pet_slots", "extra pet slot")

register_skill_node("start", "Origin", position=(0, 0), is_root=True,
    frame="root_border", sprite_name="fjol_to_sprite")

# +5 health per point, 10% increased health at 10, need 5 to pass
register_skill_node("vitality_1", "Vitality I", position=(-25, -43.3),
    max_points=10, points_to_pass=5, per_point={"mods": [("max_health", 5)]},
    at_points={10: {"mods": [("increased_max_health", 10)]}})

register_skill_node("vitality_2", "Vitality II", position=(-84.15, -102.45),
    mods=[("max_health", 50)])

FR = lambda amount: {"mods": [("fire_resistance", amount)]}
register_skill_node("fire_res_1", "Fire Resistance I", position=(-164.95, -124.1),
    max_points=5, points_to_pass=3, at_points={(1, 4): FR(1), 5: FR(3)})

NR = lambda amount: {"mods": [("nature_resistance", amount)]}
register_skill_node("nature_res_1", "Nature Resistance I", position=(-143.3, -161.6),
    max_points=5, points_to_pass=3, at_points={(1, 4): NR(1), 5: NR(3)})

FrR = lambda amount: {"mods": [("frost_resistance", amount)]}
register_skill_node("frost_res_1", "Frost Resistance I", position=(-105.8, -183.25),
    max_points=5, points_to_pass=3, at_points={(1, 4): FrR(1), 5: FrR(3)})

register_skill_node("elemental_res_1", "Elemental Resistances I", position=(-202.45, -220.75),
    mods=[("elemental_resistance", 1)])
#############################################################################################################

register_skill_node("attack_speed_1", "Attack Speed I", position=(50, 0),
    max_points=10, points_to_pass=5, per_point={"mods": [("increased_attack_speed", 3)]})

register_skill_node("attack_damage_1", "Attack Damage 1", position=(125, -25),
    max_points=10, points_to_pass=5, per_point={"mods": [("increased_attack_damage", 3)]})

#############################################################################################################

register_skill_node("swiftness_1", "Swiftness I", position=(-25, 43.3),
    max_points=10, points_to_pass=5, per_point={"mods": [("movement_speed", 2)]})

register_skill_node("swiftness_2", "Swiftness I", position=(-25, 118.3),
    mods=[("movement_speed", 20)])

#############################################################################################################

register_skill_node("titans_grip", "Titans Grip", position=(0, 300), kind="notable",
    mods=[("elemental_resistance", -20)],
    grants={"dual_wield_two_handers": True},
    description="Who needs defence when you can kill twice as fast?",
    sprite_name="titans_grip_icon")

register_skill_node("volley", "Volley", position=(1050, 200),
    mods=[("projectiles", 2),],)

# +5 fire damage to spells per point. At 10: enemies you kill have a 5% chance
# to explode for 10% of their max health as fire damage.
register_skill_node("chain_reaction", "Chain Reaction", position=(550, 200),
    max_points=10, points_to_pass=5, per_point={"mods": [("added_fire_spell", 5)]},
    at_points={10: {"effects": {"on_kill": [{"name": "explode", "chance": 5, "type": "fire",
                                             "of": "max_health", "percent": 10, "radius": 200}]}}})

register_skill_edge("start", "vitality_1")
register_skill_edge("start", "swiftness_1")
register_skill_edge("start", "attack_speed_1")
register_skill_edge("attack_speed_1", "attack_damage_1")
register_skill_edge("vitality_1", "vitality_2")
register_skill_edge("swiftness_1", "swiftness_2")
register_skill_edge("vitality_2", "fire_res_1")
register_skill_edge("vitality_2", "frost_res_1")
register_skill_edge("vitality_2", "nature_res_1")
register_skill_edge("fire_res_1", "elemental_res_1")
register_skill_edge("frost_res_1", "elemental_res_1")
register_skill_edge("nature_res_1", "elemental_res_1")

"""
# +5 health per point, extra at 10, need 5 to pass
register_skill_node("vitality", "Vitality", position=(550, 600),
    max_points=10, points_to_pass=5,
    per_point={"mods": [("max_health", 5)]},
    at_points={10: {"mods": [("increased_max_health", 10)]}})

# nothing per point - something different at every point
register_skill_node("ten_things", "Ten Things", position=(550, 400),
    max_points=10, points_to_pass=10,
    at_points={
        1: {"mods": [("max_health", 20)]},
        2: {"mods": [("pierce", 1)]},
        3: {"grants": {"ring_slots": 1}},
    })

# a notable: 1 point, its own look
register_skill_node("titans_grip", "Titans Grip", position=(550, 200), kind="notable",
    mods=[("elemental_resistance", -20)],
    grants={"dual_wield_two_handers": True},
    description="Who needs shields when you can kill twice as fast?",
    sprite_name="titans_grip_icon")

"""