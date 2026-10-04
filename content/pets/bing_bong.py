from systems.pets import make_pet_projectile_ability, register_pet, pet_item_key
from systems.gemtree import register_gem_node, register_gem_edge
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
        "damage_type": "shadow",
        "hit_type": "spell",
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
    # Auras: same lines as item stats, plus who gets them.
    rarity_overrides={
        rarity_common:    {"buffs": [{"stat": "added_fire_spell", "type": "flat", "amount": 2, "targets": ["player", "pets"]}]},
        rarity_uncommon:  {"buffs": [{"stat": "added_fire_spell", "type": "flat", "amount": 4, "targets": ["player", "pets"]}]},
        rarity_rare:      {"buffs": [{"stat": "added_fire_spell", "type": "flat", "amount": 7, "targets": ["player", "pets"]}]},
        rarity_epic:      {"buffs": [{"stat": "added_fire_spell", "type": "flat", "amount": 10, "targets": ["player", "pets"]}]},
        rarity_legendary: {"buffs": [{"stat": "added_fire_spell", "type": "flat", "amount": 12, "targets": ["player", "pets"]}, {"stat": "movement_speed",   "type": "increased", "amount": 1, "targets": ["player"]},   # legendary-only bonus
        ]},
    },
)

# --- Skill tree (same system as gem trees) ---
tree = pet_item_key("bing_bong")   # "bing_bong_pet"
register_gem_node(tree, "start", "Bing Bong", position=(800, 800), is_root=True)
register_gem_node(tree, "loud_song", "Loud Song", position=(800, 600),
                  stats=[{"stat": "buff_effect", "type": "increased", "amount": 100}])
register_gem_edge(tree, "start", "loud_song")