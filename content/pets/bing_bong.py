from systems.pets import make_pet_projectile_ability, register_pet, pet_item_key
from systems.gemtree import pet_tree
from systems.rarity import rarity_common, rarity_uncommon, rarity_rare, rarity_epic, rarity_legendary

register_pet(
    "bing_bong",
    name="Bing Bong",
    name_plural="Bing Bongers",
    sprite="bing_bong_pet_sprite",
    description="Silences enemies. Its song empowers your spells",
    item_rarity=rarity_common,
    stats={
        "ability": make_pet_projectile_ability("silence_shot_sprite", name="BING BONG!", effects=[
            {"name": "silence", "duration": 3.0},
        ]),
        "ability_cooldown": 5.0,
        "ability_range": 600,
        "ability_projectile_speed": 500,
        "ability_damage": 1,
        "hit_type": "spell",
        "damage_type": "fire",
        "blocked": {"physical"},
        "crit_damage": 150,
        "crit_chance": 8,
        "movement_speed": 100,
        "movement": "leap",
        "leap_height": 100,
        "leap_time_per_unit": 0.003,
        "leap_cooldown": 0.5,
        "leap_min_distance": 120,
        "leap_max_distance": 800,
        "leap_scatter": 60,
        "sound": "bing_bong_sound",
        "sound_interval": 60.0,
        "sound_volume": 0.6,
    },
    # Auras: a mod (same names as everywhere), how much, and who gets it.
    rarity_overrides={
        rarity_common:    {"buffs": [{"mod": "added_fire_spell", "amount": 2,  "targets": ["player", "pets"]}]},
        rarity_uncommon:  {"buffs": [{"mod": "added_fire_spell", "amount": 4,  "targets": ["player", "pets"]}]},
        rarity_rare:      {"buffs": [{"mod": "added_fire_spell", "amount": 7,  "targets": ["player", "pets"]}]},
        rarity_epic:      {"buffs": [{"mod": "added_fire_spell", "amount": 10, "targets": ["player", "pets"]}]},
        rarity_legendary: {"buffs": [{"mod": "added_fire_spell", "amount": 12, "targets": ["player", "pets"]},
                                     {"mod": "increased_movement_speed", "amount": 1, "targets": ["player"]},   # legendary-only bonus
        ]},
    },
)

# --- Skill tree (same system as gem trees) ---
tree = pet_tree(pet_item_key("bing_bong"))   # "bing_bong_pet"
tree.node("start", "Bing Bong", position=(0, 0), is_root=True)
tree.node("loud_song", "Loud Song", position=(0, -200), connects="start",
          mods=[("increased_buff_effect", 100)])