"""Active gems, basic attacks and support gems.

Pure data. Add new entries here - never in systems/.
"""

from systems.rarity import rarity_common, rarity_epic, rarity_legendary, rarity_rare, rarity_uncommon
from systems.supports import add_crit_damage, add_increased_attack_speed, add_increased_crit_chance, add_pierce, apply_orbit, burst_fire, multiply_projectiles, register_support_gem, scale_key
from systems.melee import cast_melee_attack
from systems.abilities import active_gem_templates, basic_attack_templates, basic_attacks_by_weapon, basic_attacks_by_weapon_key, build_active_gem, cast_projectile_spell, shoot_projectile_gun

from core.assets import configure_sprite

configure_sprite("gun_basic_attack_sprite", scale=1, anchor="top_left", position=(1, 1), pre_scale=4, scale_with_screen=True)

basic_attack_templates.update({
    "wand_attack": {
        "name": "Wand attack",
        "function": cast_projectile_spell,
        "sprite_name": "fireball_sprite",
        "damage_scaling": {"elemental_damage", "spell_damage"},
        "damage": 10,
        "cooldown": 0.3,
        "aoe": 0.8,
        "projectile_speed": 750,
    },

    "gun_attack": {
            "name": "Gun attack",
            "icon": "gun_basic_attack_sprite",
            "function": shoot_projectile_gun,
            "sprite_name": "gun_basic_attack_sprite",
            "damage_scaling": {"physical_damage"},
            "damage": 10,
            "cooldown": 0.05,
            "aoe": 0.2,
            "projectile_speed": 1200,
        },

    "sword_basic_attack": {
        "name": "Sword swing",
        "icon": "sword_basic_attack_icon",
        "function": cast_melee_attack,
        "sprite_name": "melee_attack_sprite",
        "hit_kind": "melee",
        "speed_stat": "attack_speed",
        "uses_aoe": False,
        "damage_scaling": {"physical_damage", "attack_damage"},
        "damage": 50,
        "attack_time": 1,
        "projectile_speed": 0,
        "range_mult": 1.0,
        "arc": 0,              # over 360 bliver til en slags spin, kinda cool til cyclone agtige ting
        "swing_time": 0.7,
        "sprite_angle_offset": 0.0,   # sat til 100 eller over bliver nærmest en slags blade storm
    },
})

basic_attacks_by_weapon_key.update({
    "sword":        "sword_basic_attack",
    "axe":          "sword_basic_attack",
    "mace":         "sword_basic_attack",
    "greatsword":   "sword_basic_attack",
    "wand":         "wand_attack",
    "staff":        "wand_attack",
    "gun":          "gun_attack",
    None:           "wand_attack",
})

basic_attacks_by_weapon.update({
    weapon_class: build_active_gem(basic_attack_templates[key], [])
    for weapon_class, key in basic_attacks_by_weapon_key.items()
})

active_gem_templates.update({
    "fireball": {
        "name": "Fireball",
        "function": cast_projectile_spell,
        "sprite_name": "fireball_sprite",
        "weapon_tags": {"caster"},
        "support_tags": {"projectile", "damage", "aoe", "crit"},
        "damage_scaling": {"elemental_damage", "spell_damage"},
        "aoe": 1,
        "projectile_speed": 600,
        "rarity_stats": {
            rarity_common:    {"damage": 70,  "cooldown": 1,    "crit_chance": 3,},
            rarity_uncommon:  {"damage": 95,  "cooldown": 0.90, "crit_chance": 4,},
            rarity_rare:      {"damage": 130, "cooldown": 0.85, "crit_chance": 5,},
            rarity_epic:      {"damage": 175, "cooldown": 0.80, "crit_chance": 6,},
            rarity_legendary: {"damage": 240, "cooldown": 0.75, "crit_chance": 7,},
        },
    },

    "shadow_bolt": {
        "name": "Shadow Bolt",
        "function": cast_projectile_spell,
        "sprite_name": "shadow_bolt_sprite",
        "weapon_tags": {"caster"},
        "support_tags": {"projectile", "damage", "aoe", "dot", "crit"},
        "damage_scaling": {"elemental_damage", "spell_damage"},
        "aoe": 2,
        "projectile_speed": 350,
        "dot_duration": 3,
        "rarity_stats": {
            rarity_common:    {"damage": 25,  "dot_damage": 25},
            rarity_uncommon:  {"damage": 42,  "dot_damage": 37},
            rarity_rare:      {"damage": 65,  "dot_damage": 55},
            rarity_epic:      {"damage": 90,  "dot_damage": 77},
            rarity_legendary: {"damage": 112, "dot_damage": 105},
        },
    },

    "cleave": {
        "name": "Cleave",
        "icon": "cleave_icon",
        "function": cast_melee_attack,
        "sprite_name": "melee_attack_sprite",
        "hit_kind": "melee",
        "speed_stat": "attack_speed",
        "uses_aoe": False,
        "weapon_tags": {"melee"},
        "support_tags": {"damage", "melee", "crit", "attack"},
        "damage_scaling": {"physical_damage", "attack_damage"},
        "projectile_speed": 0,
        "range_mult": 1.1,
        "arc": 140,
        "swing_time": 0.9,
        "sprite_angle_offset": 0.0,
        "locks_movement": True,
        "lock_duration": 0.6,
        "rarity_stats": {
            rarity_common:    {"damage": 60,  "attack_time": 0.60, "crit_chance": 4, "crit_damage": 10},
            rarity_uncommon:  {"damage": 85,  "attack_time": 0.56, "crit_chance": 5, "crit_damage": 20},
            rarity_rare:      {"damage": 120, "attack_time": 0.52, "crit_chance": 6, "crit_damage": 30},
            rarity_epic:      {"damage": 165, "attack_time": 0.48, "crit_chance": 7, "crit_damage": 40},
            rarity_legendary: {"damage": 225, "attack_time": 0.44, "crit_chance": 8, "crit_damage": 50},
        },
    },

    "spin_attack": {
            "name": "Spin Attack",
            "icon": "cleave_icon",
            "function": cast_melee_attack,
            "sprite_name": "melee_attack_sprite",
            "hit_kind": "melee",
            "speed_stat": "attack_speed",
            "uses_aoe": False,
            "weapon_tags": {"melee"},
            "support_tags": {"damage", "melee", "crit", "attack"},
            "damage_scaling": {"physical_damage", "attack_damage"},
            "projectile_speed": 0,
            "range_mult": 1,
            "arc": 1080,
            "swing_time": 1,
            "sprite_angle_offset": 0.0,
            "locks_movement": False,
            "lock_duration": 0.0,
            "rarity_stats": {
                rarity_common:    {"damage": 60,  "attack_time": 0.60, "crit_chance": 4, "crit_damage": 10},
                rarity_uncommon:  {"damage": 85,  "attack_time": 0.56, "crit_chance": 5, "crit_damage": 20},
                rarity_rare:      {"damage": 120, "attack_time": 0.52, "crit_chance": 6, "crit_damage": 30},
                rarity_epic:      {"damage": 165, "attack_time": 0.48, "crit_chance": 7, "crit_damage": 40},
                rarity_legendary: {"damage": 225, "attack_time": 0.44, "crit_chance": 8, "crit_damage": 50},
            },
        },

    "shotgun_blast": {
            "name": "Shotgun Blast",
            "function": shoot_projectile_gun,
            "sprite_name": "gun_basic_attack_sprite",
            "weapon_tags": {"gun"},
            "support_tags": {"projectile", "damage", "crit"},
            "damage_scaling": {"physical_damage"},
            "cooldown": 0.05,
            "aoe": 0.2,
            "projectile_speed": 1200,
            "rarity_stats": {
                rarity_common:    {"damage": 25},
                rarity_uncommon:  {"damage": 42},
                rarity_rare:      {"damage": 65},
                rarity_epic:      {"damage": 90},
                rarity_legendary: {"damage": 112},
            },
        },
})

register_support_gem(
    "projectiles", "Multiple Projectiles",
    tiers={
        rarity_common:    (1, 2),
        rarity_uncommon:  (3, 4),
        rarity_rare:      (5, 6),
        rarity_epic:      (7, 8),
        rarity_legendary: (9, 10),
    },
    apply=multiply_projectiles,
    describe=lambda gem: f"+{gem.value} projectiles",
    tags=["projectile"],
)

register_support_gem(
    "speed", "Projectile Speed",
    tiers={
        rarity_common:    (1.10, 1.25),
        rarity_uncommon:  (1.25, 1.45),
        rarity_rare:      (1.45, 1.70),
        rarity_epic:      (1.70, 2.00),
        rarity_legendary: (2.00, 2.50),
    },
    apply=scale_key("speed"),
    describe=lambda gem: f"x{gem.value:.2f} projectile speed",
    tags=["projectile"],
)

register_support_gem(
    "aoe", "Increased Area",
    tiers={
        rarity_common:    (1.10, 1.20),
        rarity_uncommon:  (1.20, 1.35),
        rarity_rare:      (1.35, 1.55),
        rarity_epic:      (1.55, 1.80),
        rarity_legendary: (1.80, 2.20),
    },
    apply=scale_key("aoe"),
    describe=lambda gem: f"x{gem.value:.2f} area of effect",
    tags=["aoe"],
)

register_support_gem(
    "damage", "More Damage",
    tiers={
        rarity_common:    (1.10, 1.20),
        rarity_uncommon:  (1.20, 1.35),
        rarity_rare:      (1.35, 1.55),
        rarity_epic:      (1.55, 1.80),
        rarity_legendary: (1.80, 2.20),
    },
    apply=scale_key("damage"),
    describe=lambda gem: f"x{gem.value:.2f} damage",
    tags=["damage"]
)

register_support_gem(
    "dot_damage", "Increased DoT",
    tiers={
        rarity_common:    (1.10, 1.20),
        rarity_uncommon:  (1.20, 1.35),
        rarity_rare:      (1.35, 1.55),
        rarity_epic:      (1.55, 1.80),
        rarity_legendary: (1.80, 2.20),
    },
    apply=scale_key("dot_damage"),
    describe=lambda gem: f"x{gem.value:.2f} damage over time",
    tags=["dot"]
)

register_support_gem(
    "crit_chance", "Increased Crit Chance Support",
    tiers={
        rarity_common:    (70, 90),
        rarity_uncommon:  (91, 110),
        rarity_rare:      (111, 130),
        rarity_epic:      (131, 150),
        rarity_legendary: (151, 200),
    },
    apply=add_increased_crit_chance,
    describe=lambda gem: f"{gem.value:.0f}% increased critical strike chance",
    tags=["crit"]
)

register_support_gem(
    "crit_damage", "Increased Crit Damage Support",
    tiers={
        rarity_common:    (20, 30),
        rarity_uncommon:  (30, 45),
        rarity_rare:      (45, 65),
        rarity_epic:      (65, 90),
        rarity_legendary: (90, 130),
    },
    apply=add_crit_damage,
    describe=lambda gem: f"{gem.value:.0f}% increased critical strike damage",
    tags=["crit"],
)

register_support_gem(
    "burst", "Burst Fire",
    tiers={
        rarity_common:    (1, 1),
        rarity_uncommon:  (2, 2),
        rarity_rare:      (3, 3),
        rarity_epic:      (4, 4),
        rarity_legendary: (5, 5),
    },
    apply=burst_fire,
    describe=lambda gem: f"+{int(gem.value)} extra casts, x{1.5 + (int(gem.value) - 1) * 0.25:.2f} cooldown",
    tags=["projectile"],
)

register_support_gem(
    "pierce", "Pierce",
    tiers={
        rarity_common:    (1, 1),
        rarity_uncommon:  (2, 2),
        rarity_rare:      (3, 3),
        rarity_epic:      (4, 4),
        rarity_legendary: (5, 5),
    },
    apply=add_pierce,
    describe=lambda gem: f"Pierces {int(gem.value)} enemies",
    tags=["projectile"],
)

register_support_gem(
    "orbit", "Orbiting Projectiles",
    tiers={
        rarity_common:    (150, 180),
        rarity_uncommon:  (180, 220),
        rarity_rare:      (220, 270),
        rarity_epic:      (270, 330),
        rarity_legendary: (330, 400),
    },
    apply=apply_orbit,
    describe=lambda gem: f"Projectiles orbit at {gem.value:.0f} range",
    tags=["projectile"],
)

register_support_gem(
    "attack_speed", "Increased attack speed",
    tiers={
        rarity_common:    (2, 5),
        rarity_uncommon:  (6, 10),
        rarity_rare:      (11, 15),
        rarity_epic:      (16, 25),
        rarity_legendary: (26, 40),
    },
    apply=add_increased_attack_speed,
    describe=lambda gem: f"{gem.value:.0f}% Increased attack speed",
    tags=["attack"],
)


