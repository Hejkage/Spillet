from systems.items import base_items
from systems.rarity import rarity_unique

base_items.update({
    "herbicide": {
        "base": "jeweled_ring",
        "name": "Herbicide",
        "rarity": rarity_unique,
        "min_monster_tier": 3,
        "mods": [
            ("poison_immunity", 100),
            ("nature_resistance", -25),
            ("poison_chance", 10),
            ("poison_max_stacks", (1, 10)),
            ("verdancy", (10, 20))
        ],
        "grants": {"all_damage_can_poison": True},
    },
})