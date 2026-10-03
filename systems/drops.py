import random

from systems.rarity import drop_context

# region Item drops

class DropEntry:
    def __init__(self, item_factory, weight=1, min_amount=1, max_amount=1, min_tier=0, max_tier=None):
        self.item_factory = item_factory
        self.weight = weight
        self.min_amount = min_amount
        self.max_amount = max_amount
        # Which monster tiers may drop this at all. This is how a unique is
        # held back until tier 5, or an early item stops dropping late.
        self.min_tier = min_tier
        self.max_tier = max_tier

    def allowed_at(self, monster_tier):
        if monster_tier < self.min_tier:
            return False
        if self.max_tier is not None and monster_tier > self.max_tier:
            return False
        return True

def entries_for_tier(entries, monster_tier):
    return [e for e in entries if e.allowed_at(monster_tier)]

def roll_from_group(entries):
    def factory():
        usable = entries_for_tier(entries, drop_context.monster_tier)
        weights = [e.weight for e in usable]
        if not usable or sum(weights) <= 0:
            return None
        entry = random.choices(usable, weights=weights, k=1)[0]
        return entry.item_factory()
    return factory

def roll_drop_count(drop_count):
    """How many times a pool rolls. Two ways to write it:

      (0, 4)                        every number 0-4 equally likely
      {0: 60, 1: 20, 2: 12, 3: 6, 4: 2}   your own odds per number

    The dict is how you say "most of the time nothing, rarely four".
    Weights are relative, so they do not have to add up to 100.
    """
    if isinstance(drop_count, dict):
        counts = list(drop_count)
        weights = [drop_count[c] for c in counts]
        if not counts or sum(weights) <= 0:
            return 0
        return random.choices(counts, weights=weights, k=1)[0]
    lo, hi = drop_count
    return random.randint(lo, hi)

class DropPool:
    def __init__(self, entries=None, drop_count=(0, 2)):
        self.entries = entries if entries is not None else []
        self.drop_count = drop_count

    def add_entry(self, item_factory, weight=1, min_amount=1, max_amount=1):
        self.entries.append(DropEntry(item_factory, weight, min_amount, max_amount))
    
    def add_group(self, group):
        self.entries.extend(group)

    def roll(self, extra_drops=0):
        """extra_drops comes from the monster's RANK - a legendary monster
        rolls this pool many more times than a normal one."""
        if not self.entries:
            return []

        usable = entries_for_tier(self.entries, drop_context.monster_tier)
        if not usable:
            return []

        num_drops = roll_drop_count(self.drop_count) + extra_drops
        if num_drops <= 0:
            return []

        weights = [e.weight for e in usable]
        if sum(weights) <= 0:
            return []
        dropped = []
        for _ in range(num_drops):
            entry = random.choices(usable, weights=weights, k=1)[0]
            amount = random.randint(entry.min_amount, entry.max_amount)
            for _ in range(amount):
                item = entry.item_factory()
                if item is not None:
                    dropped.append(item)
        return dropped

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
generic_drop_pool = DropPool(drop_count=(1, 1))


# ---------------------------------------------------------------
# REGISTRY - content/drops.py fills this in, and register_active_gem()
# appends to it automatically.
# ---------------------------------------------------------------
active_gem_group = []
pet_group = []          # filled by register_pet()
