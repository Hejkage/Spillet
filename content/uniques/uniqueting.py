from systems.items import base_items
from systems.rarity import rarity_unique

base_items.update({
    "ember_crown": {
        "base": "leather_helmet",
        "name": "Ember Crown",
        "rarity": rarity_unique,
        "min_monster_tier": 3,
        "stats": [
            {"stat": "fire_damage", "type": "increased", "amount": (20, 40)},
            {"stat": "burn_immunity", "type": "flat", "amount": 1},
            {"stat": "fire_resistance", "type": "flat", "amount": 25},
        ],
        "mods":    [("projectiles", 1)],
        "grants":  {"ring_slots": 1},
        "effects": {"on_kill": [{"name": "explode", "radius": 150, "damage": (100, 200), "damage_type": "fire"}]},
        "summons": {"spider": 1},
    },
})