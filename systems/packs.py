import math
import random

# region Monster packs
#
# A pack is a group of enemies that spawns together at one spot.
# It is built the same way as a drop pool, so it should feel familiar:
#
#   PackEntry       one enemy type + how many of it        (like DropEntry)
#   register_pack   names a pack so content can reuse it
#   PackPool        a weighted list of packs to pick from  (like DropPool)
#
# WHO decides WHAT:
#   the pack  - which monsters, and how many of each
#   the area  - which packs may spawn, and how many packs
#   the area  - the level everything in it is built from
#
# A pack spawns EVERY one of its entries. The pool is what picks WHICH pack.

class PackEntry:
    def __init__(self, enemy_type, count=(1, 1), tier_offset=None,
                 rank_weights=None, rank_only=None, extra=None):
        self.enemy_type = enemy_type
        self.count = count
        # Leave these out unless this particular monster is special.
        self.tier_offset = tier_offset        # e.g. (1, 2) for "tougher than the area"
        # rank_weights CHANGES some odds and keeps the rest:
        #   {"rare": 900}  -> usually rare, but still sometimes normal
        # rank_only REPLACES the whole list, so nothing else can be rolled:
        #   {"rare": 5, "epic": 2}  -> always rare or epic, never normal
        self.rank_weights = rank_weights
        self.rank_only = rank_only
        self.extra = extra or {}              # anything else set on the enemy

    def roll_count(self):
        lo, hi = self.count
        return random.randint(lo, hi)

class Pack:
    def __init__(self, entries, spread=140):
        self.entries = entries
        self.spread = spread      # how far from the spot its members stand

    def roll(self):
        """-> [(enemy_type, offset_x, offset_y, entry), ...]"""
        members = []
        for entry in self.entries:
            for _ in range(entry.roll_count()):
                angle = math.radians(random.uniform(0, 360))
                dist = random.uniform(0, self.spread)
                members.append((entry.enemy_type,
                                math.cos(angle) * dist,
                                math.sin(angle) * dist,
                                entry))
        return members

class PackPool:
    """A weighted list of pack names. One roll picks one pack."""
    def __init__(self, entries=None):
        self.entries = entries if entries is not None else []   # [(pack_name, weight)]

    def add(self, pack_name, weight=1):
        self.entries.append((pack_name, weight))

    def roll(self):
        if not self.entries:
            return None
        names = [name for name, _ in self.entries]
        weights = [w for _, w in self.entries]
        if sum(weights) <= 0:
            return None
        return random.choices(names, weights=weights, k=1)[0]

pack_tier_offset = (0, 0)       # a tier 5 area spawns tier 5 monsters

def roll_enemy_tier(area_tier, entry):
    lo, hi = entry.tier_offset if entry.tier_offset else pack_tier_offset
    return area_tier + random.randint(lo, hi)

# ---------------------------------------------------------------
# HOW SPOTS ARE CHOSEN - swap this later for area level, danger, quests...
# register_spot_picker("dangerous", fn) then spawn_packs(..., picker="dangerous")
# ---------------------------------------------------------------
spot_pickers = {}

def register_spot_picker(name, fn):
    spot_pickers[name] = fn

def pick_random(spots, count, area):
    return random.sample(spots, min(count, len(spots)))

register_spot_picker("random", pick_random)

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
pack_configs = {}

def register_pack(key, entries, spread=140):
    if key in pack_configs:
        raise ValueError(f"Pack '{key}' is registered twice")
    pack_configs[key] = Pack(entries, spread)
    return key
#endregion