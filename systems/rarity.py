import random

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Rarity
rarity_common = "common"
rarity_uncommon = "uncommon"
rarity_rare = "rare"
rarity_epic = "epic"
rarity_legendary = "legendary"
rarity_unique = "unique"

# The LADDER that random items roll on. Unique is not on it: a unique always
# is unique (its base item says "rarity": rarity_unique), it is never rolled.
rarity_order = [rarity_common, rarity_uncommon, rarity_rare, rarity_epic, rarity_legendary]

# Every rarity, in the order the loot filter and sorting show them.
all_rarities = rarity_order + [rarity_unique]

# ---------------------------------------------------------------
# MONSTER TIER -> HOW GOOD A DROP CAN BE
#
# Every monster has a tier from 1 to 10. The tier caps the RARITY of the
# items it drops, and because an item's rarity already decides how strong
# its mods may roll, the mods are capped with it. A tier 1 monster cannot
# drop a legendary vest at all.
#
# Each base item says which monster tier it needs for each rarity:
#
#   "tier_shift": 5     the whole table moves 5 tiers up (a late-game base)
#   "rarity_tiers": {rarity_legendary: 9}    override one rarity exactly
#
# So a leather belt (no shift) can drop as legendary from tier 4 monsters,
# and a dragonforged chestplate ("tier_shift": 5) needs tier 9.
# ---------------------------------------------------------------
monster_tier_min = 0      # tier 0 is the base: no scaling at all
monster_tier_max = 10     # 11 tiers in total, 0 to 10

rarity_tier_requirements = {
    rarity_common:    0,
    rarity_uncommon:  0,
    rarity_rare:      3,
    rarity_epic:      6,
    rarity_legendary: 9,
}

class DropContext:
    """Who is dropping right now. spawn_drops() fills this in, and
    roll_item() reads it so content keeps writing plain lambdas."""
    def __init__(self):
        self.monster_tier = monster_tier_max    # shops and debug: no limit
        self.rank = None

    def set(self, monster_tier=None, rank=None):
        self.monster_tier = monster_tier_max if monster_tier is None else monster_tier
        self.rank = rank

    def clear(self):
        self.monster_tier = monster_tier_max
        self.rank = None

drop_context = DropContext()

def rarity_tier_required(base, rarity):
    """Which monster tier this base item needs before it can drop at `rarity`."""
    overrides = base.get("rarity_tiers", {})
    if rarity in overrides:
        return overrides[rarity]
    return rarity_tier_requirements[rarity] + base.get("tier_shift", 0)

def max_item_rarity(base, monster_tier):
    """The best rarity this base may drop at, from a monster of this tier."""
    best = rarity_common
    for rarity in rarity_order:
        if monster_tier >= rarity_tier_required(base, rarity):
            best = rarity
    return best

def cap_rarity(rarity, cap):
    return cap if rarity_order.index(rarity) > rarity_order.index(cap) else rarity

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

def roll_item(base_key, rarity=None, monster_tier=None):
    """Make an item from base_items[base_key]. Normal bases and uniques both go here.

    A base with a fixed "rarity" (every unique) always has that rarity.
    Otherwise the rarity is rolled and capped by the monster's tier.
    The item gets the base's fixed parts ("stats", "mods", "grants", "effects",
    "summons", with every (low, high) rolled) plus random affixes from "affixes"."""
    from systems.items import EquippableItem, affix_count_by_rarity, affix_entries, affix_pool, resolve_base
    from systems.bonuses import roll_bonuses
    base = resolve_base(base_key)
    if monster_tier is None:
        monster_tier = drop_context.monster_tier
    if "rarity" in base:
        rarity = base["rarity"]
    else:
        if rarity is None:
            rarity = roll_rarity(drop_context.rank and rank_item_rarity_weights(drop_context.rank))
        # the monster's tier is the ceiling: no legendary vests off a tier 1 monster
        rarity = cap_rarity(rarity, max_item_rarity(base, monster_tier))

    rolled = roll_bonuses(base)
    stats = rolled.pop("stats", [])

    lo, hi = affix_count_by_rarity.get(rarity, (0, 0))      # uniques: (0, 0) = no random affixes
    entries = affix_entries(base) if base.get("affixes") and hi > 0 else []
    if entries:
        available = [key for key, _ in entries]
        weights = [weight for _, weight in entries]
        allowed_tiers = roll_rarity_tier_range(rarity)
        for _ in range(random.randint(lo, hi)):
            affix_key = random.choices(available, weights=weights, k=1)[0]
            affix = affix_pool[affix_key]
            tier = random.choice(allowed_tiers)
            amount = roll_affix_value(affix, tier)
            stats.append({"stat": affix["stat"], "type": affix["type"], "amount": amount, "tier": tier})

    return EquippableItem(base["name"], base["sprite"], base["slot"], stats=stats, rarity=rarity,
                          weapon_class=base.get("weapon_class"), swing_sprite_name=base.get("swing_sprite"),
                          base_key=base_key, **rolled)

def rank_item_rarity_weights(rank):
    """A rank may push dropped items towards higher rarities. None = normal odds."""
    from systems.monsters import monster_ranks
    config = monster_ranks.get(rank)
    return config.get("rarity_weights") if config else None

rarity_colors = {
    rarity_common: (255, 255, 255),
    rarity_uncommon: (100, 220, 200),
    rarity_rare: (70, 130, 255),
    rarity_epic: (170, 70, 255),
    rarity_legendary: (255, 165, 0),
    rarity_unique: (200, 60, 60),
}
