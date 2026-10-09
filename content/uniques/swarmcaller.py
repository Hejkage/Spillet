import random
from systems.items import base_items
from systems.rarity import rarity_unique
from systems.pets import roll_pets

# Which pets Swarmcaller can summon, and how likely each is.
# Higher = more common. A pet that isn't listed is never summoned.
swarmcaller_pet_weights = {
    "spider": 1,
    "bing_bong": 1,
    "flatworm": 1,
}
swarmcaller_pet_count = (1, 8)

def roll_swarmcaller():
    """Random parts a plain range can't describe: which pets, and how many of each."""
    count = random.randint(*swarmcaller_pet_count)
    pets = roll_pets(swarmcaller_pet_weights, count)          # e.g. ["spider", "spider", "bing_bong"]
    return {"summons": {pet: pets.count(pet) for pet in set(pets)}}

base_items.update({
    "swarmcaller": {
        "base": "wooden_staff",              # sprite, slot and weapon class come from here
        "name": "Swarmcaller",
        "rarity": rarity_unique,
        "min_monster_tier": 5,            # item_drop() won't drop it from lower tiers
        "roll": roll_swarmcaller,
    },
})
