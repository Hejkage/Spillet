from systems.pets import make_pet_projectile_ability, register_pet
from systems.rarity import rarity_common, rarity_legendary

register_pet(
    "spider",
    name="Spider",
    name_plural="Spiders",
    sprite="spider_pet_sprite",
    item_rarity=rarity_common,
    drop_weight=0.1, drop_rarity=rarity_legendary,
    stats={
        "ability": make_pet_projectile_ability("web_shot_sprite", effects=[
            {"name": "slow", "duration": 2.0, "amount": 0.4},
        ]),
        "ability_cooldown": 1,
        "ability_range": 500,
        "ability_projectile_speed": 300,
        "ability_damage": 25,
        "speed": 300,
    },
)
