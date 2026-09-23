import random
from systems.items import register_unique
from systems.pets import roll_pets

swarmcaller_pet_count = (1, 8)

# Which pets Swarmcaller can summon, and how likely each is.
# Higher = more common. A pet that isn't listed is never summoned.
swarmcaller_pet_weights = {
    "spider": 1,
    "bing_bong": 1,
}

def roll_swarmcaller():
    lo, hi = swarmcaller_pet_count
    count = random.randint(lo, hi)
    return {"summon_pets": roll_pets(swarmcaller_pet_weights, count)}

register_unique(
    "swarmcaller",
    roll=roll_swarmcaller,
    name="Swarmcaller",
    sprite_name="wand_item_sprite",
    slot_type="weapon",
    weapon_class="wand",
)
