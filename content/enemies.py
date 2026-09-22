"""Enemy abilities and enemy definitions.

Pure data. Add new entries here - never in systems/.
"""

from systems.rarity import rarity_common
from systems.items import make_item
from systems.drops import generic_drop_pool
from systems.enemies import EnemyProjectileAbility, enemy_configs
from .drops import example_drop_pool

generic_drop_pool.add_entry(lambda: make_item("gold_coin"), weight=1, min_amount=1, max_amount=10)

#Enemy Spells and attacks
def witch_wand_attack():
    return EnemyProjectileAbility(cooldown=1.2, ability_range=500, damage=150, speed=400, sprite_name="shadow_bolt_sprite")

def witch_meteor():
    return EnemyProjectileAbility(cooldown=5.0, ability_range=600, damage=300, speed=250, sprite_name="fireball_sprite", aoe=2.5)

enemy_configs.update({
    "witch": {
        "base_sprite": "witch_front_sprite",
        "health": 100,
        "xp_value": 50,
        "move_speed": 150,
        "contact_damage": 5,
        "behavior": "caster",
        "attack_range": 400,
        "cast_cooldown": 0.5,
        "cast_time": 0.5,
        "abilities": [witch_wand_attack, witch_meteor],
        "drop_pool": example_drop_pool,
    },

    "baby_witch": {
        "base_sprite": "witch_front_sprite",
        "sprite_scale": 0.5,
        "health": 100,
        "xp_value": 25,
        "move_speed": 100,
        "contact_damage": 5,
        "behavior": "caster",
        "attack_range": 300,
        "cast_cooldown": 1,
        "cast_time": 0.5,
        "abilities": [witch_wand_attack, witch_meteor],
        "guaranteed_drops": [
            lambda: make_item("fireball_gem", rarity=rarity_common),
            lambda: make_item("baby_wand",),
        ],
        "skip_generic_drops": True,
    },

    "slime_frog": {
            "base_sprite": "slime_frog_sprite",
            "health": 100,
            "xp_value": 500,
            "move_speed": 80,
            "contact_damage": 100,
            "behavior": "leaper",
            "leap_range": 500,
            "leap_height": 120,
            "leap_time_per_unit": 0.0030,
            "leap_min_distance": 120,
            "leap_max_distance": 400,
            "leap_scatter": 60,
            "leap_cooldown": 4.0,
            "abilities": [],
            "drop_pool": example_drop_pool,
        },
})

