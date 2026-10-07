"""Drop groups and drop pools.

Pure data. Add new entries here - never in systems/.
"""

from systems.rarity import rarity_epic, rarity_legendary, rarity_rare, roll_item, roll_rarity
from systems.items import make_item, make_unique, unique_drop
from systems.drops import DropEntry, DropPool, roll_from_group
from systems.pets import pet_item_key

flat_to_spell_group = [
    DropEntry(lambda: make_item("support_added_nature_spell", rarity=roll_rarity()), weight=33),
    DropEntry(lambda: make_item("support_added_fire_spell",   rarity=roll_rarity()), weight=33),
    DropEntry(lambda: make_item("support_added_frost_spell",  rarity=roll_rarity()), weight=33),
    DropEntry(lambda: make_item("support_added_pure_spell",   rarity=roll_rarity()), weight=0.5),
    DropEntry(lambda: make_item("support_added_shadow_spell", rarity=roll_rarity()), weight=0.5),
]

flat_to_attack_group = [
    DropEntry(lambda: make_item("support_added_nature_attack",   rarity=roll_rarity()), weight=24.75),
    DropEntry(lambda: make_item("support_added_fire_attack",     rarity=roll_rarity()), weight=24.75),
    DropEntry(lambda: make_item("support_added_frost_attack",    rarity=roll_rarity()), weight=24.75),
    DropEntry(lambda: make_item("support_added_physical_attack", rarity=roll_rarity()), weight=24.75),
    DropEntry(lambda: make_item("support_added_pure_attack",     rarity=roll_rarity()), weight=0.5),
    DropEntry(lambda: make_item("support_added_shadow_attack",   rarity=roll_rarity()), weight=0.5),
]

support_gem_group = [
    DropEntry(lambda: make_item("support_projectiles",       rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_speed",             rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_aoe",               rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_damage",            rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_dot",               rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_burst",             rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_pierce",            rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_orbit",             rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_crit_chance",       rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_crit_damage",       rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_attack_speed",      rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("support_burn_chance",       rarity=roll_rarity()), weight=5),
    DropEntry(roll_from_group(flat_to_spell_group),                                 weight=5),
    DropEntry(roll_from_group(flat_to_attack_group),                                weight=5),
]

active_gem_group = [
    DropEntry(lambda: make_item("fireball_gem",             rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("shadow_bolt_gem",          rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("cleave_gem",               rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("spin_attack_gem",          rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("shotgun_blast_gem",        rarity=roll_rarity()), weight=5),
    DropEntry(lambda: make_item("elemental_projectile_gem", rarity=roll_rarity()), weight=5),
]

def pet_drop(pet_type, weight):
    """One pet as a drop entry. pet_drop("spider", 5) drops a "spider_pet" item with a rolled rarity."""
    return DropEntry(lambda: make_item(pet_item_key(pet_type), rarity=roll_rarity()), weight=weight)

# Rolled ONLY after "a flatworm" has been picked in pet_group below.
flatworm_group = [
    pet_drop("fire_flatworm",     24),
    pet_drop("frost_flatworm",    24),
    pet_drop("nature_flatworm",   24),
    pet_drop("physical_flatworm", 24),
    pet_drop("shadow_flatworm",    1),
    pet_drop("pure_flatworm",      1),
]

pet_group = [
    pet_drop("spider",    5),
    pet_drop("bing_bong", 5),
    DropEntry(roll_from_group(flatworm_group), weight=5),   # the whole flatworm group = ONE entry
]

leather_armor_group = [
    DropEntry(lambda: roll_item("leather_helmet"),      weight=25),
    DropEntry(lambda: roll_item("leather_body"),        weight=25),
    DropEntry(lambda: roll_item("leather_pants"),       weight=25),
    DropEntry(lambda: roll_item("leather_boots"),       weight=25),
    DropEntry(lambda: roll_item("leather_gloves"),      weight=25),
    DropEntry(lambda: roll_item("leather_belt"),        weight=25),
    DropEntry(lambda: roll_item("wooden_shield"),       weight=25),
    DropEntry(lambda: make_item("unique_item_test"),    weight=0.001),        # TEST ITEM TEST ITEM TEST ITEM TEST ITEM!!!!!!!!!!!!
]

low_level_weapons_group = [
    DropEntry(lambda: roll_item("twig_wand"),   weight=25),
    DropEntry(lambda: roll_item("short_sword"), weight=25),
    DropEntry(lambda: roll_item("basic_gun"),   weight=25),
]

low_level_jewelry_group = [
    DropEntry(lambda: roll_item("jeweled_necklace"), weight=25),
    DropEntry(lambda: roll_item("jeweled_ring"),     weight=25),
]

unique_group = [
    #Omega god tier 0.1 weighting!
    DropEntry(lambda: make_item("unique_item_test"),    weight=1),      # TEST ITEM TEST ITEM TEST ITEM TEST ITEM!!!!!!!!!!!!
    DropEntry(lambda: make_unique("swarmcaller"),       weight=0.001),
]

wand_group = [
    DropEntry(lambda: make_unique("swarmcaller"),   weight=25),
    DropEntry(lambda: roll_item("twig_wand"),       weight=25),
]

# pet_group is filled by register_pet() in content/pets/

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

legendary_only_pool = DropPool([
    DropEntry(lambda: roll_item("heavy_golden_armor", rarity=rarity_legendary), weight=60),
    unique_drop("swarmcaller", weight=40),
], drop_count=(3, 3))




# ============================================================================
# A DROP POOL - every setting it understands.
# Goes in content/drops.py.
#
#   DropEntry  one thing that can drop
#   group      a plain list of entries you can reuse across pools
#   DropPool   what one monster rolls on when it dies
# ============================================================================

# A group is just a list, so you can spread it into several pools.
frost_armour_group = [
    DropEntry(
        lambda: roll_item("heavy_golden_armor"),   # what to make. ALWAYS a lambda
        weight=25,          # picked this often against the other entries
        min_amount=1,       # how many copies when this entry is picked
        max_amount=1,
        min_tier=1,         # lowest monster tier that may drop it at all
        max_tier=None,      # None = no upper limit. 3 = stops dropping after tier 3
    ),
    DropEntry(lambda: roll_item("leather_body"), weight=40),
    DropEntry(lambda: roll_item("leather_helmet"), weight=40),
]

# Uniques: unique_drop() reads min_monster_tier from the unique itself,
# so the rule lives next to the unique and not here.
frost_unique_group = [
    unique_drop("swarmcaller", weight=0.5),
    # unique_drop("swarmcaller", weight=0.5, min_tier=8),   # override it here instead
]

# A currency entry: one entry, many copies.
coin_group = [
    DropEntry(lambda: make_item("gold_coin"), weight=100, min_amount=3, max_amount=12),
]

frost_pool = DropPool(
    [
        *frost_armour_group,
        *frost_unique_group,
        *coin_group,
        DropEntry(lambda: make_item("fireball_gem", rarity=roll_rarity()), weight=5),
    ],
    drop_count={0: 60, 1: 20, 2: 12, 3: 6, 4: 2},   # 60% nothing, 2% four items - A monster's RANK adds more rolls on top of this.
) 