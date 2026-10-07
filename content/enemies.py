from systems.rarity import rarity_common
from systems.items import make_item
from systems.drops import generic_drop_pool
from systems.enemies import EnemyProjectileAbility, enemy_configs
from .drops import example_drop_pool, frost_pool

generic_drop_pool.add_entry(lambda: make_item("gold_coin"), weight=1, min_amount=1, max_amount=10)

#Enemy Spells and attacks
def witch_wand_attack():
    return EnemyProjectileAbility(cooldown=3, ability_range=500, damage=150, speed=400, sprite_name="shadow_bolt_sprite", damage_type="shadow", hit_type="attack")

def witch_meteor():
    return EnemyProjectileAbility(cooldown=12, ability_range=600, damage=300, speed=250, sprite_name="fireball_sprite", aoe=2.5, damage_type="fire", hit_type="spell")

enemy_configs.update({
    "witch": {
        "base_sprite": "witch_front_sprite",
        "back_sprite": "witch_back_sprite",
        "health": 1000,
        "xp_value": 50,
        "move_speed": 150,
        "contact_damage": 0,
        "behavior": "caster",
        "defence": {"fire_resistance": 50},
        "attack_range": 400,
        "cast_cooldown": 2,
        "cast_time": 1,
        "abilities": [witch_wand_attack, witch_meteor],
        "tier_scaling": {
                    "health":         2.0,
                    "contact_damage": 1.4,
                    "xp_value":       1.5,
                    "ability_damage": 1.6,
                    "move_speed":     1.1,
                },
        "tier_stats": {
                    5:  {"ability_projectiles_mult": 2},
                    10: {"ability_projectiles_mult": 3},
                },
        "drop_pool": example_drop_pool,
    },

    "baby_witch": {
        "base_sprite": "witch_front_sprite",
        "back_sprite": "witch_back_sprite",
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

    "target_dummy": {
        "base_sprite": "witch_front_sprite",
        "back_sprite": "witch_back_sprite",
        "health": 100000000,
        "xp_value": 0,
        "move_speed": 0,
        "contact_damage": 0,
        "behavior": "caster",
        "attack_range": 0,
        "cast_cooldown": 0.5,
        "cast_time": 0.5,
        "abilities": [],
        "drop_pool": None,
        "show_hit_stats": True,
        "defence": {"fire_resistance": 50, "frost_resistance": 25, "elemental_protection": 10, "shadow_protection": 50},
    },
})


# ============================================================================
# A MONSTER - every setting it understands.
# Goes in enemy_configs in content/enemies.py.
# Anything you leave out comes from enemy_defaults in systems/enemies.py.
# ============================================================================
enemy_configs.update({
    "frost_wraith": {
        # --- looks -------------------------------------------------------
        "base_sprite":  "witch_front_sprite",   # facing the player
        "back_sprite":  "witch_back_sprite",    # walking away. None = reuse base
        "sprite_scale": 1.0,                    # 2.0 = twice as big on screen

        # --- tier 1 stats (every tier is built from these) ---------------
        "health":          100,
        "contact_damage":  5,       # damage for touching the player. 0 = none
        "xp_value":        50,
        "move_speed":      120,

        # --- how it behaves ----------------------------------------------
        "behavior":          "caster",   # melee / caster / leaper, or your own
        "attack_range":      450,        # how close before it attacks
        "retreat_range":     150,        # caster: backs off inside this
        "retreat_speed_mult": 0.65,      # caster: retreats slower than it chases
        "cast_time":         0.5,        # wind-up before a spell lands
        "cast_cooldown":     0.4,        # pause after any cast
        "collision_radius":  None,       # None = from the sprite. 40 = wide body

        # --- leaper only --------------------------------------------------
        "leap_range":         500,
        "leap_height":        120,
        "leap_time_per_unit": 0.0015,
        "leap_max_distance":  500,
        "leap_min_distance":  0,
        "leap_cooldown":      2.5,
        "leap_scatter":       0,

        # --- what it does -------------------------------------------------
        "abilities": [witch_wand_attack],      # functions from this file

        # --- TIER SCALING -------------------------------------------------
        # Its own curve: stat = tier 1 value * factor ** (tier - 1).
        # Only the stats you name here differ from the global curve in
        # systems/monsters.py. 1.0 means "do not scale at all".
        "tier_scaling": {
            "health":           1.8,
            "contact_damage":   1.4,
            "xp_value":         1.5,
            "ability_damage":   1.6,
            "move_speed":       1.0,
            # timers: BELOW 1.0 = faster. Floors live in systems/monsters.py
            "cast_time":        0.93,
            "cast_cooldown":    0.95,
            "ability_cooldown": 0.90,
        },

        # Exact values at exact tiers. These WIN over any curve, so this is
        # where you hand-tune the tiers that matter. Tiers you skip keep
        # using the curve above.
        "tier_stats": {
            5:  {"health": 900, "contact_damage": 20, "ability_damage_mult": 6,
                 "cast_time": 0.30, "ability_cooldown_mult": 0.5, "ability_projectiles_mult": 2},
            10: {"health": 25000, "contact_damage": 60, "ability_damage_mult": 40,
                 "move_speed": 200, "xp_value": 5000, "ability_projectiles_mult": 2},
        },

        # --- loot ---------------------------------------------------------
        "drop_pool":        frost_pool,        # a DropPool from content/drops.py
        "guaranteed_drops": [],                # e.g. [lambda: make_item("gold_coin")]
        "skip_generic_drops": False,           # True = no coins from generic_drop_pool
        "drop_tier":        None,              # 10 = always drops like a tier 10 monster
    },
})