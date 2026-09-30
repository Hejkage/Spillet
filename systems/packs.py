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
    def __init__(self, enemy_type, count=(1, 1), level_offset=None, tier_weights=None, extra=None):
        self.enemy_type = enemy_type
        self.count = count
        # Leave these out unless this particular monster is special.
        self.level_offset = level_offset      # e.g. (0, 3) for "runs a bit higher"
        self.tier_weights = tier_weights      # e.g. {"rare": 20} for "often rare"
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

# ---------------------------------------------------------------
# MONSTER LEVEL
#
# Every spawned enemy gets .level. Nothing reads it yet - when you add
# levels for real, read enemy.level in systems/enemies.py and in
# spawn_drops(), and everything below already feeds it.
# ---------------------------------------------------------------
pack_level_offset = (-2, 1)     # a level 54 area spawns level 52-55 monsters

def roll_enemy_level(area_level, entry):
    lo, hi = entry.level_offset if entry.level_offset else pack_level_offset
    return max(1, area_level + random.randint(lo, hi))

# ---------------------------------------------------------------
# MONSTER TIER  (normal / rare / epic ... like PoE's blue and yellow packs)
#
# Nothing is registered yet, so every monster comes out "normal" and nothing
# changes. When you add tiers, one call per tier is all this needs:
#
#     register_enemy_tier("rare", weight=8, apply=make_rare)
#
# `apply(enemy)` is where its stats, size, aura or loot bonus go.
# ---------------------------------------------------------------
default_tier = "normal"
enemy_tiers = {}

def register_enemy_tier(name, weight=1, apply=None, **settings):
    enemy_tiers[name] = {"weight": weight, "apply": apply, **settings}
    return name

def roll_enemy_tier(area_level, entry):
    weights = {name: cfg["weight"] for name, cfg in enemy_tiers.items()}
    if entry.tier_weights:
        weights.update(entry.tier_weights)          # this monster's own odds
    names = [n for n, w in weights.items() if w > 0]
    if not names:
        return default_tier
    return random.choices(names, weights=[weights[n] for n in names], k=1)[0]

def apply_enemy_tier(enemy):
    """Runs the tier's own code, once, right after the enemy is created."""
    config = enemy_tiers.get(getattr(enemy, "tier", default_tier))
    if config and config["apply"]:
        config["apply"](enemy)

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