"""Monster ranks: normal / uncommon / rare / epic / legendary.

Pure data. The rank decides how MANY and how GOOD items a monster drops,
and may buff the monster itself. Tier (1-10) is separate - see the area's
`tier` and systems/monsters.py.
"""

from systems.monsters import register_monster_rank
from systems.rarity import (rarity_common, rarity_uncommon, rarity_rare,
                            rarity_epic, rarity_legendary)

register_monster_rank(
    "normal",
    weight=1000,
    drop_count=(0, 0),            # just whatever its drop pool rolls
    color=(220, 220, 220),
)

register_monster_rank(
    "uncommon",
    weight=250,
    drop_count={1: 75, 2: 25},    # 75% one item, 25% two, needs {}
    stat_mult={"health": 1.8, "xp_value": 2,},
    ability_mult={"projectiles": 2},  
    color=(100, 220, 200),
)

register_monster_rank(
    "rare",
    weight=80,
    drop_count=(2, 4),  # 33% two, 33% three 33% four
    stat_mult={"health": 3.5, "contact_damage": 1.4, "xp_value": 4},
    color=(70, 130, 255),
)

register_monster_rank(
    "epic",
    weight=10,
    drop_count=(4, 7),
    stat_mult={"health": 7, "contact_damage": 1.8, "xp_value": 9},
    ability_mult={"damage": 3.0, "cooldown": 0.5},
    color=(170, 70, 255),
)

register_monster_rank(
    "legendary",
    weight=1,
    drop_count={8:50, 9:25, 10:10, 11:10, 12:5},
    stat_mult={"health": 15, "contact_damage": 2.5, "xp_value": 25},
    ability_mult={"damage": 5.0, "cooldown": 0.4, "projectiles": 3},
    color=(255, 165, 0),
)