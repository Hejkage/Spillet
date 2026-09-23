"""Affixes, weapon classes, base items and item templates.

Pure data. Add new entries here - never in systems/.
"""

from systems.rarity import rarity_common, rarity_epic, rarity_legendary, rarity_rare, rarity_uncommon
from systems.weapons import weapon_class_configs
from systems.items import affix_count_by_rarity, affix_pool, base_items, item_templates

affix_pool.update({
    "spell_damage": {
        "stat": "spell_damage",
        "type": "increased",
        "tiers": {
            rarity_common:    (5, 10),
            rarity_uncommon:  (10, 18),
            rarity_rare:      (18, 30),
            rarity_epic:      (30, 45),
            rarity_legendary: (45, 65),
        },
    },

    "elemental_damage": {
        "stat": "elemental_damage",
        "type": "increased",
        "tiers": {
            rarity_common:    (5, 10),
            rarity_uncommon:  (10, 18),
            rarity_rare:      (18, 30),
            rarity_epic:      (30, 45),
            rarity_legendary: (45, 65),
        },
    },

    "physical_damage": {
        "stat": "physical_damage",
        "type": "increased",
        "tiers": {
            rarity_common:    (5, 10),
            rarity_uncommon:  (10, 18),
            rarity_rare:      (18, 30),
            rarity_epic:      (30, 45),
            rarity_legendary: (45, 65),
        },
    },

    "attack_damage": {
        "stat": "attack_damage",
        "type": "increased",
        "tiers": {
            rarity_common:    (5, 10),
            rarity_uncommon:  (10, 18),
            rarity_rare:      (18, 30),
            rarity_epic:      (30, 45),
            rarity_legendary: (45, 65),
        },
    },

    "attack_speed": {
        "stat": "attack_speed",
        "type": "increased",
        "tiers": {
            rarity_common:    (3, 6),
            rarity_uncommon:  (6, 10),
            rarity_rare:      (10, 15),
            rarity_epic:      (15, 21),
            rarity_legendary: (21, 30),
        },
    },

    "flat_movement_speed": {
        "stat": "movement_speed",
        "type": "flat",
        "tiers": {
            rarity_common:    (5, 15),
            rarity_uncommon:  (15, 30),
            rarity_rare:      (30, 50),
            rarity_epic:      (50, 75),
            rarity_legendary: (75, 110),
        },
    },

    "increased_movement_speed": {
        "stat": "movement_speed",
        "type": "increased",
        "tiers": {
            rarity_common:    (5, 10),
            rarity_uncommon:  (10, 18),
            rarity_rare:      (18, 30),
            rarity_epic:      (30, 45),
            rarity_legendary: (45, 65),
        },
    },

    "aoe": {
        "stat": "aoe",
        "type": "flat",
        "tiers": {
            rarity_common:    (5, 15),
            rarity_uncommon:  (15, 30),
            rarity_rare:      (30, 50),
            rarity_epic:      (50, 75),
            rarity_legendary: (75, 110),
        },
    },

    "max_health": {
        "stat": "max_health",
        "type": "flat",
        "tiers": {
            rarity_common:    (50, 100),
            rarity_uncommon:  (101, 200),
            rarity_rare:      (201, 300),
            rarity_epic:      (301, 500),
            rarity_legendary: (500, 1000),
        },
    },

    "health_regen": {
        "stat": "health_regen",
        "type": "flat",
        "tiers": {
            rarity_common:    (1, 2),
            rarity_uncommon:  (3, 5),
            rarity_rare:      (6, 10),
            rarity_epic:      (11, 25),
            rarity_legendary: (26, 50),
        },
    },

    "cooldown": {
        "stat": "cooldown",
        "type": "flat",
        "tiers": {
            rarity_common:    (1, 2),
            rarity_uncommon:  (3, 4),
            rarity_rare:      (5, 6),
            rarity_epic:      (7, 8),
            rarity_legendary: (9, 10),
        },
    },

    "lifesteal": {
        "stat": "lifesteal",
        "type": "flat",
        "tiers": {
            rarity_common:    (1, 3),
            rarity_uncommon:  (3, 5),
            rarity_rare:      (5, 8),
            rarity_epic:      (8, 12),
            rarity_legendary: (12, 18),
        },
    },

    "increased_crit_chance": {
        "stat": "crit_chance",
        "type": "increased",
        "tiers": {
            rarity_common:    (10, 20),
            rarity_uncommon:  (20, 35),
            rarity_rare:      (35, 55),
            rarity_epic:      (55, 80),
            rarity_legendary: (80, 120),
        },
    },

    "flat_crit_chance": {
        "stat": "crit_chance",
        "type": "flat",
        "tiers": {
            rarity_common:    (0.5, 1),
            rarity_uncommon:  (1, 1.5),
            rarity_rare:      (1.5, 2.5),
            rarity_epic:      (2.5, 4),
            rarity_legendary: (4, 6),
        },
    },

    "crit_damage": {
        "stat": "crit_damage",
        "type": "flat",
        "tiers": {
            rarity_common:    (5, 10),
            rarity_uncommon:  (10, 20),
            rarity_rare:      (20, 35),
            rarity_epic:      (35, 55),
            rarity_legendary: (55, 90),
        },
    },

    "attack_range": {
        "stat": "attack_range",
        "type": "flat",
        "tiers": {
            rarity_common:    (5, 12),
            rarity_uncommon:  (12, 22),
            rarity_rare:      (22, 35),
            rarity_epic:      (35, 55),
            rarity_legendary: (55, 85),
        },
    },
})

affix_count_by_rarity.update({
    rarity_common:    (1, 2),
    rarity_uncommon:  (2, 3),
    rarity_rare:      (3, 4),
    rarity_epic:      (5, 6),
    rarity_legendary: (7, 8),
})

weapon_class_configs.update({
    "sword":      {"name": "Sword",      "tags": {"melee", "one_hand"}},
    "axe":        {"name": "Axe",        "tags": {"melee", "one_hand"}},
    "mace":       {"name": "Mace",       "tags": {"melee", "one_hand"}},
    "greatsword": {"name": "Greatsword", "tags": {"melee", "two_hand"}},
    "wand":       {"name": "Wand",       "tags": {"caster", "one_hand"}},
    "staff":      {"name": "Staff",      "tags": {"caster", "two_hand"}},
    "bow":        {"name": "Bow",        "tags": {"ranged", "two_hand"}},
    "gun":        {"name": "Gun",        "tags": {"ranged", "one_hand"}},
})

base_items.update({
    "short_sword": {
        "name": "Short Sword",
        "sprite": "sword_item_sprite",
        "swing_sprite": "melee_attack_sprite",
        "slot": "weapon",
        "weapon_class": "sword",
        "affixes": ["aoe", "cooldown", "crit_damage", "increased_crit_chance", "lifesteal", "elemental_damage", "physical_damage", "attack_damage", "attack_speed", "attack_range"],
    },

    "leather_belt": {
        "name": "Leather belt",
        "sprite": "belt_item_sprite",
        "slot": "belt",
        "affixes": ["aoe", "cooldown", "crit_damage", "increased_crit_chance", "lifesteal", "physical_damage"],
    },

    "twig_wand": {
        "name": "Twig wand",
        "sprite": "wand_item_sprite",
        "slot": "weapon",
        "weapon_class": "wand",
        "affixes": ["aoe", "cooldown", "crit_damage", "increased_crit_chance", "lifesteal", "elemental_damage", "physical_damage", "spell_damage"],
    },

    "basic_gun": {
            "name": "Basic Gun",
            "sprite": "basic_gun_item_sprite",
            "slot": "weapon",
            "weapon_class": "gun",
            "affixes": ["cooldown", "crit_damage", "increased_crit_chance", "lifesteal", "physical_damage"],
        },

    "wooden_shield": {
        "name": "Wooden shield",
        "sprite": "shield_item_sprite",
        "slot": "offhand",
        "affixes": ["aoe", "cooldown", "crit_damage", "increased_crit_chance", "lifesteal", "attack_speed"],
    },

    "jeweled_ring": {
        "name": "Jeweled ring",
        "sprite": "ring_item_sprite",
        "slot": "ring",
        "affixes": ["aoe", "cooldown", "crit_damage", "increased_crit_chance", "elemental_damage", "spell_damage", "max_health"],
    },

    "jeweled_necklace": {
        "name": "Jeweled necklace",
        "sprite": "necklace_item_sprite",
        "slot": "neck",
        "affixes": ["aoe", "cooldown", "crit_damage", "increased_crit_chance", "elemental_damage", "spell_damage", "max_health"],
    },

    "leather_body": {
        "name": "Leather body armor",
        "sprite": "body_item_sprite",
        "slot": "body",
        "affixes": ["aoe", "cooldown", "max_health", "health_regen"],
    },

    "leather_helmet": {
        "name": "Leather helmet",
        "sprite": "helmet_item_sprite",
        "slot": "head",
        "affixes": ["aoe", "cooldown", "spell_damage", "max_health", "health_regen"],
    },

    "leather_boots": {
        "name": "Leather boots",
        "sprite": "boots_item_sprite",
        "slot": "boots",
        "affixes": ["aoe", "cooldown", "flat_movement_speed", "increased_movement_speed", "max_health", "health_regen"],
    },

    "leather_pants": {
        "name": "Leather pants",
        "sprite": "pants_item_sprite",
        "slot": "pants",
        "affixes": ["aoe", "cooldown", "flat_movement_speed", "max_health", "health_regen"],
    },

    "leather_gloves": {
        "name": "Leather gloves",
        "sprite": "gloves_item_sprite",
        "slot": "gloves",
        "affixes": ["aoe", "cooldown", "max_health", "health_regen", "elemental_damage", "physical_damage", "spell_damage"],
    },
})

item_templates.update({
    # Equipment (uniques)
    "baby_wand": {
    "kind": "equippable",
    "name": "Baby witch wand",
    "sprite": "wand_item_sprite",
    "slot": "weapon",
    "weapon_class": "wand",
    "stats": {
        #First is just a name
        "Just a name": {"stat": "spell_damage", "type": "increased", "amount": 5},
        "elemental_damage": {"stat": "elemental_damage", "type": "increased", "amount": 5},
    },
    "rarity": rarity_common,
    },

    "increased_dmg_sword": {
        "kind": "equippable",
        "name": "Sword",
        "sprite": "sword_item_sprite",
        "swing_sprite": "melee_attack_sprite",
        "slot": "weapon",
        "weapon_class": "sword",
        "stats": {
            "increased_spell_damage": {"stat": "spell_damage", "type": "increased", "amount": 10},
        },
        "rarity": rarity_common,
    },

    "Unique_item_test": {
        "kind": "equippable",
        "name": "Helmet",
        "sprite": "helmet_item_sprite",
        "slot": "helmet",
        "stats": {
            "increased_spell_damage": {"stat": "max_health", "type": "increased", "amount": 1000},
            "increased_spell_damage": {"stat": "max_health", "type": "increased", "amount": 1000},
            "increased_spell_damage": {"stat": "max_health", "type": "increased", "amount": 1000},
            "increased_spell_damage": {"stat": "max_health", "type": "increased", "amount": 1000},
            "increased_spell_damage": {"stat": "max_health", "type": "increased", "amount": 1000},
            "increased_spell_damage": {"stat": "max_health", "type": "increased", "amount": 1000},
        },
        "rarity": rarity_legendary,
    },

    # Active gems items (Does not do anything but create gem items)
    "fireball_gem": {
        "kind": "active_gem",
        "name": "Fireball Gem",
        "sprite": "fireball_item_sprite",
        "template_key": "fireball",
        "rarity": rarity_common,
    },

    "shadow_bolt_gem": {
        "kind": "active_gem",
        "name": "Shadow Bolt Gem",
        "sprite": "shadow_bolt_sprite",
        "template_key": "shadow_bolt",
        "rarity": rarity_rare,
    },

     "cleave_gem": {
        "kind": "active_gem",
        "name": "Cleave Gem",
        "sprite": "melee_attack_sprite",
        "template_key": "cleave",
        "rarity": rarity_rare,
    },

    "spin_attack_gem": {
            "kind": "active_gem",
            "name": "Spin Attack Gem",
            "sprite": "melee_attack_sprite",
            "template_key": "spin_attack",
            "rarity": rarity_rare,
        },

    "shotgun_blast_gem": {
                "kind": "active_gem",
                "name": "Shotgun Blast Gem",
                "sprite": "gun_basic_attack_sprite",
                "template_key": "shotgun_blast",
                "rarity": rarity_rare,
            },

    # Support gems items (Does not do anything but create gem items)
    "support_projectiles": {"kind": "support_gem", "gem_type": "projectiles", "rarity": rarity_common},
    "support_speed":       {"kind": "support_gem", "gem_type": "speed",       "rarity": rarity_common},
    "support_aoe":         {"kind": "support_gem", "gem_type": "aoe",         "rarity": rarity_common},
    "support_damage":      {"kind": "support_gem", "gem_type": "damage",      "rarity": rarity_common},
    "support_dot":         {"kind": "support_gem", "gem_type": "dot_damage",  "rarity": rarity_common},
    "support_burst":       {"kind": "support_gem", "gem_type": "burst",       "rarity": rarity_common},
    "support_pierce":      {"kind": "support_gem", "gem_type": "pierce",      "rarity": rarity_common},
    "support_orbit":       {"kind": "support_gem", "gem_type": "orbit",       "rarity": rarity_common},
    "support_crit_chance": {"kind": "support_gem", "gem_type": "crit_chance", "rarity": rarity_common},
    "support_crit_damage": {"kind": "support_gem", "gem_type": "crit_damage", "rarity": rarity_common},
    "support_attack_speed":{"kind": "support_gem", "gem_type": "attack_speed","rarity": rarity_common},

    # Pet items are made by register_pet() in content/pets/

    # Currency
    "gold_coin": {
        "kind": "currency",
        "name": "Gold Coin",
        "sprite": "gold_coin_sprite",
    },
})

