import random

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Rarity
rarity_common = "common"
rarity_uncommon = "uncommon"
rarity_rare = "rare"
rarity_epic = "epic"
rarity_legendary = "legendary"

rarity_order = [rarity_common, rarity_uncommon, rarity_rare, rarity_epic, rarity_legendary]

def roll_rarity(weights=None):
    if weights is None:
        weights = {
            rarity_common:    60,
            rarity_uncommon:  25,
            rarity_rare:      10,
            rarity_epic:      4,
            rarity_legendary: 1,
        }
    rarities = list(weights.keys())
    chances = list(weights.values())
    return random.choices(rarities, weights=chances, k=1)[0]

def roll_rarity_tier_range(rarity):
    max_index = rarity_order.index(rarity)
    return rarity_order[:max_index + 1]

def roll_affix_value(affix, tier_rarity):
    low, high = affix["tiers"][tier_rarity]
    if isinstance(low, int) and isinstance(high, int):
        return random.randint(low, high)
    return round(random.uniform(low, high), 3)

def roll_item(base_key, rarity=None):
    from systems.items import EquippableItem, affix_count_by_rarity, affix_pool, base_items
    base = base_items[base_key]
    if rarity is None:
        rarity = roll_rarity()

    lo, hi = affix_count_by_rarity[rarity]
    count = random.randint(lo, hi)

    available = list(base["affixes"])
    count = min(count, len(available))
    chosen = random.sample(available, count)

    allowed_tiers = roll_rarity_tier_range(rarity)

    stats = {}
    for affix_key in chosen:
        affix = affix_pool[affix_key]
        tier = random.choice(allowed_tiers)
        amount = roll_affix_value(affix, tier)
        stats[affix_key] = {"stat": affix["stat"], "type": affix["type"], "amount": amount, "tier": tier}

    return EquippableItem(base["name"], base["sprite"], base["slot"], stats=stats, rarity=rarity, weapon_class=base.get("weapon_class"), swing_sprite_name=base.get("swing_sprite"))

rarity_colors = {
    rarity_common: (255, 255, 255),
    rarity_uncommon: (100, 220, 200),
    rarity_rare: (70, 130, 255),
    rarity_epic: (170, 70, 255),
    rarity_legendary: (255, 165, 0),
}
unique_color = (200, 60, 60)
