import random

# region Item drops

class DropEntry:
    def __init__(self, item_factory, weight=1, min_amount=1, max_amount=1):
        self.item_factory = item_factory
        self.weight = weight
        self.min_amount = min_amount
        self.max_amount = max_amount

def roll_from_group(entries):
    def factory():
        weights = [e.weight for e in entries]
        if not entries or sum(weights) <= 0:
            return None
        entry = random.choices(entries, weights=weights, k=1)[0]
        return entry.item_factory()
    return factory

class DropPool:
    def __init__(self, entries=None, drop_count=(0, 2)):
        self.entries = entries if entries is not None else []
        self.drop_count = drop_count

    def add_entry(self, item_factory, weight=1, min_amount=1, max_amount=1):
        self.entries.append(DropEntry(item_factory, weight, min_amount, max_amount))
    
    def add_group(self, group):
        self.entries.extend(group)

    def roll(self):
        if not self.entries:
            return []

        lo, hi = self.drop_count
        num_drops = random.randint(lo, hi)
        if num_drops <= 0:
            return []

        weights = [e.weight for e in self.entries]
        if sum(weights) <= 0:
            return []
        dropped = []
        for _ in range(num_drops):
            entry = random.choices(self.entries, weights=weights, k=1)[0]
            amount = random.randint(entry.min_amount, entry.max_amount)
            for _ in range(amount):
                dropped.append(entry.item_factory())
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
