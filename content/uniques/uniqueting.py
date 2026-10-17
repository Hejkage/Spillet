from systems.items import base_items
from systems.rarity import rarity_unique

base_items.update({
    "ember_crown": {
        "base": "leather_helmet",
        "name": "Ember Crown",
        "rarity": rarity_unique,
        "min_monster_tier": 3,
        "mods": [
            ("increased_fire_damage", (20, 40)),
            ("burn_immunity", 100),
            ("fire_resistance", 25),
            ("projectiles", 1),
        ],
        "grants":  {"ring_slots": 1},
        # killed enemies explode for 5-10% of their max health as fire damage
        "effects": {"on_kill": [{"name": "explode", "type": "fire", "of": "max_health",
                                 "percent": (5, 10), "radius": 150}]},
        "summons": {"spider": 1},
    },
})