from systems.pets import make_pet_projectile_ability, register_pet
from systems.rarity import rarity_rare, rarity_legendary

register_pet(
    "bing_bong",
    name="Bing Bong",
    name_plural="Bing Bongers",
    sprite="bing_bong_pet_sprite",
    item_rarity=rarity_rare,
    drop_weight=0.1, drop_rarity=rarity_legendary,
    stats={
        "ability": make_pet_projectile_ability("silence_shot_sprite", effects=[
            {"name": "silence", "duration": 3.0},
        ]),
        "ability_cooldown": 5.0,
        "ability_range": 600,
        "ability_projectile_speed": 500,
        "ability_damage": 5,
        "speed": 100,
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
)
