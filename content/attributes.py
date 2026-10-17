"""The attributes: Creation, Domination, Efficiency.

Each one is a stat (give it on items / tree nodes like any stat:
("domination", 20)) that also gives bonuses:

    per_point    given for every point
    checkpoints  given once you have that many points - each one can be different

Both use the same parts as items: mods, grants, effects, summons (systems/bonuses.py).
Fill them in when you know what each attribute should do. Example:

    register_attribute("domination", "Domination", color=(220, 90, 70),
        per_point={"mods": [("max_health", 2)]},
        checkpoints={
            100: {"mods": [("increased_physical_damage", 10)]},
            250: {"mods": [("arc", 20)]},
            500: {"grants": {"dual_wield_two_handers": True}},
        })
"""
from systems.attributes import register_attribute

register_attribute("creation",   "Creation",   color=(0, 0, 155),
    description="Pets and summons",
    per_point={},
    every={10: {"mods": [("increased_pet_buff_effect", 1)]}},      # 1% per 10 Creation
    checkpoints={})

register_attribute("domination", "Domination", color=(190, 0, 0),
    description="Physical, attacks and health",
    per_point={"mods": [("max_health", 2), ("increased_physical_damage", 0.1)]},
    checkpoints={})

register_attribute("efficiency", "Efficiency", color=(50, 205, 50),
    description="Speed, dodge and stealth",
    per_point={},
    checkpoints={})

register_attribute("duality", "Duality", color=(95, 0, 160),
    description="Light and dark",
    per_point={},
    checkpoints={})

register_attribute("verdancy", "Verdancy", color=(35, 100, 50),
    description="Nature effects and powers",
    per_point={},
    checkpoints={})