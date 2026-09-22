"""Drop groups and drop pools.

Pure data. Add new entries here - never in systems/.
"""

from systems.rarity import rarity_epic, rarity_legendary, rarity_rare, roll_item, roll_rarity
from systems.items import make_item
from systems.drops import DropEntry, DropPool, active_gem_group
from .items import roll_swarmcaller

support_gem_group = [
    DropEntry(lambda: make_item("support_projectiles", rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_speed",       rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_aoe",         rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_damage",      rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_dot",         rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_burst",       rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_pierce",      rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_orbit",       rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_crit_chance", rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_crit_damage", rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_attack_speed",rarity=roll_rarity()), weight=5),
]

active_gem_group.extend([
    DropEntry(lambda: make_item("fireball_gem",    rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("shadow_bolt_gem", rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("cleave_gem",      rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("spin_attack_gem", rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("shotgun_blast_gem", rarity=roll_rarity()), weight=5000),
])

leather_armor_group = [
    DropEntry(lambda: roll_item("leather_helmet"), weight=25),
    DropEntry(lambda: roll_item("leather_body"),   weight=25),
    DropEntry(lambda: roll_item("leather_pants"),  weight=25),
    DropEntry(lambda: roll_item("leather_boots"),  weight=25),
    DropEntry(lambda: roll_item("leather_gloves"), weight=25),
    DropEntry(lambda: roll_item("leather_belt"),   weight=25),
    DropEntry(lambda: roll_item("wooden_shield"),  weight=25),
]

low_level_weapons_group = [
    DropEntry(lambda: roll_item("twig_wand"),   weight=25),
    DropEntry(lambda: roll_item("short_sword"), weight=25),
    DropEntry(lambda: roll_item("basic_gun"),   weight=500000),
]

low_level_jewelry_group = [
    DropEntry(lambda: roll_item("jeweled_necklace"), weight=25),
    DropEntry(lambda: roll_item("jeweled_ring"),     weight=25),
]

unique_group = [
    #Omega god tier 0.1 weighting!
    DropEntry(lambda: roll_swarmcaller(), weight=0.1),
]

wand_group = [
    DropEntry(lambda: roll_swarmcaller(),          weight=25),
    DropEntry(lambda: roll_item("twig_wand"),      weight=25),
]

pet_group = [
    DropEntry(lambda: make_item("spider_pet", rarity=rarity_legendary),    weight=0.1),
    DropEntry(lambda: make_item("bing_bong_pet", rarity=rarity_legendary), weight=0.1),
]

example_drop_pool = DropPool([
    # Currency 
    DropEntry(lambda: make_item("gold_coin"),weight=0, min_amount=1, max_amount=5),
    # Equippable item — rarity omitted, so it uses the template's default rarity.
    DropEntry(lambda: make_item("baby_wand"), weight=0),
    # Equippable item with a rarity override — same template, forced legendary.
    DropEntry(lambda: make_item("increased_dmg_sword", rarity=rarity_legendary), weight=0),
    # Support gem — rarity override changes the rolled value range.
    DropEntry(lambda: make_item("support_damage", rarity=roll_rarity({rarity_rare: 50, rarity_epic: 35, rarity_legendary: 15})), weight=0),
    # Randomly rolled legendary 
    DropEntry(lambda: roll_item("leather_boots", rarity=rarity_legendary), weight=0),
    *low_level_weapons_group,
    *leather_armor_group,
    *support_gem_group,
    *active_gem_group,
    *low_level_jewelry_group,
    *unique_group,
    *pet_group,
], drop_count = (0 , 2))

