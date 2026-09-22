"""Pet definitions.

Pure data. Add new entries here - never in systems/.
"""

from systems.pets import make_pet_projectile_ability, pet_configs

pet_configs.update({
    "spider": {
        "sprite": "spider_pet_sprite",
        "name": "Spider",
        "name_plural": "Spiders",
        "stats": {
            "ability": make_pet_projectile_ability("web_shot_sprite", effects=[
                {"name": "slow", "duration": 2.0, "amount": 0.4},
            ]),
            "ability_cooldown": 1,
            "ability_range": 500,
            "ability_projectile_speed": 300,
            "ability_damage": 25,
            "speed": 300,
        },
    },

    "bing_bong": {
        "name": "Bing Bong",
        "name_plural": "Bing Bongers",
        "sprite": "bing_bong_pet_sprite",
        "stats": {
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
    },
})

