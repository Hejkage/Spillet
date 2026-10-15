"""BONUSES - what an item or a skill tree node GIVES the player.

Items and skill tree nodes use the SAME five parts, written the same way:

  stats     plain stat lines     [{"stat": "max_health", "type": "flat", "amount": 50}]
  mods      mechanics for every ability that fits them (systems/mods.py)
                                 [("projectiles", 2), ("pierce", 1)]
  grants    permissions / counts other systems ask about
                                 {"ring_slots": 1, "dual_wield_two_handers": True}
  effects   things that happen on an event ("on_kill", ...)
                                 {"on_kill": [{"name": "explode", "radius": 200, "damage": 250}]}
  summons   pets that follow you while you have it
                                 {"spider": 2, "bing_bong": 1}

So a unique that gives +2 projectiles, or a tree node that summons a spider,
needs no new code: the player collects all five from every equipped item and
every allocated node in recalculate_stats().

RANGES: in an item definition any number can be a range, (low, high).
It is rolled ONCE when the item is made:
    {"stat": "spell_damage", "type": "increased", "amount": (20, 40)}
    ("projectiles", (1, 3))
    {"on_kill": [{"name": "explode", "radius": 200, "damage": (150, 300)}]}
"""
import random

bonus_parts = ("stats", "mods", "grants", "effects", "summons")


def get_part(source, part):
    """Read one part from a skill node (a dict) or an item (an object)."""
    if isinstance(source, dict):
        return source.get(part)
    return getattr(source, part, None)


# ---------------------------------------------------------------
# ROLLING - (low, high) -> a number, everywhere inside a definition
# ---------------------------------------------------------------
def is_range(value):
    return (isinstance(value, tuple) and len(value) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value))

def roll_ranges(value):
    """A copy of `value` with every (low, high) replaced by a rolled number."""
    if is_range(value):
        low, high = value
        if isinstance(low, int) and isinstance(high, int):
            return random.randint(low, high)
        return round(random.uniform(low, high), 3)
    if isinstance(value, dict):
        return {k: roll_ranges(v) for k, v in value.items()}
    if isinstance(value, list):
        return [roll_ranges(v) for v in value]
    if isinstance(value, tuple):
        return tuple(roll_ranges(v) for v in value)
    return value

def roll_bonuses(definition):
    """{part: rolled copy} for every part the definition has.
    If it has a "roll" function, what it returns is ADDED on top
    (lists are extended, dicts are merged) - for random parts that a
    simple range can't describe."""
    rolled = {part: roll_ranges(definition[part]) for part in bonus_parts if definition.get(part)}
    roll = definition.get("roll")
    if roll:
        for part, value in roll().items():
            if part not in bonus_parts:
                raise ValueError(f"roll() returned '{part}', which is not one of {bonus_parts}")
            value = roll_ranges(value)
            if part not in rolled:
                rolled[part] = value
            elif isinstance(value, dict) and part != "effects":
                for k, v in value.items():                       # grants / summons add up
                    rolled[part][k] = rolled[part].get(k, 0) + v
            elif isinstance(value, dict):
                for event, effects in value.items():
                    rolled[part].setdefault(event, []).extend(effects)
            else:
                rolled[part] = list(rolled[part]) + list(value)
    return rolled


# ---------------------------------------------------------------
# SCALING - "per point" bonuses (skill tree nodes, attributes)
# ---------------------------------------------------------------
def scale_part(part, value, times):
    """One part given `times` times: +5 health per point at 7 points = +35 health.
    Used by skill tree nodes and attributes."""
    if part == "stats":
        return [dict(line, amount=line.get("amount", 0) * times) for line in value]
    if part == "mods":
        return [mod for mod in value for _ in range(times)]          # each point is its own copy
    if part == "grants":
        return {k: (v if v is True else v * times) for k, v in value.items()}
    if part == "summons":
        return {k: v * times for k, v in value.items()}
    if part == "effects":
        return {event: [e for e in effects for _ in range(times)] for event, effects in value.items()}
    return value

def add_part(total, part, value):
    """Add one part into a {part: ...} total (lists extend, grants/summons add up)."""
    if part in ("stats", "mods"):
        total.setdefault(part, []).extend(value)
    elif part == "effects":
        for event, effects in value.items():
            total.setdefault(part, {}).setdefault(event, []).extend(effects)
    else:                                                            # grants / summons add up
        bucket = total.setdefault(part, {})
        for k, v in value.items():
            bucket[k] = True if v is True else bucket.get(k, 0) + v

# ---------------------------------------------------------------
# COLLECTING - everything the player has, added together
# ---------------------------------------------------------------
def collect_bonuses(sources):
    """sources = [(source_key, item_or_node), ...]
    -> {"stats": [...], "mods": [...], "grants": {...}, "effects": {...},
        "summons": [(source_key, pet_type, number), ...]}"""
    from systems.mods import mod_types
    totals = {"stats": [], "mods": [], "grants": {}, "effects": {}, "summons": []}
    for source_key, source in sources:
        totals["stats"].extend(get_part(source, "stats") or ())
        for name, value in get_part(source, "mods") or ():
            if name in mod_types:
                totals["mods"].append((name, value))
        for name, value in (get_part(source, "grants") or {}).items():
            totals["grants"][name] = totals["grants"].get(name, 0) + (1 if value is True else value)
        for event, effects in (get_part(source, "effects") or {}).items():
            totals["effects"].setdefault(event, []).extend(effects)
        for pet_type, count in (get_part(source, "summons") or {}).items():
            for number in range(int(count)):
                totals["summons"].append((source_key, pet_type, number))
    return totals


# ---------------------------------------------------------------
# DESCRIBING - the lines tooltips show
# ---------------------------------------------------------------
grant_labels = {}

def register_grant_label(name, label):
    """What a grant is called in tooltips. Without one: "ring_slots" -> "Ring slots"."""
    grant_labels[name] = label

def grant_label(name):
    return grant_labels.get(name) or name.replace("_", " ").capitalize()

def describe_stat_line(line):
    from systems.items import stat_defs, stat_label, stat_is_percent
    stat = line.get("stat")
    amount = line.get("amount", 0)
    label = stat_label(stat)
    if stat in stat_defs and stat_defs[stat]["flag"]:
        return label                                        # "Immune to Poison"
    if line.get("type") == "increased":
        if amount < 0:
            return f"{-amount:g}% reduced {label}"               # -10 -> "10% reduced"
        return f"+{amount:g}% increased {label}"
    suffix = "%" if stat_is_percent(stat) else ""
    return f"{amount:+g}{suffix} {label}"                         # +20 / -20

def merged_stat_lines(stat_lines):
    """+1 fire res and +2 fire res -> one line, +3 fire res. Only for showing; the
    numbers the player gets are the same either way."""
    merged = {}
    for line in stat_lines:
        key = (line.get("stat"), line.get("type"))
        if key in merged:
            merged[key] = dict(merged[key], amount=merged[key].get("amount", 0) + line.get("amount", 0))
        else:
            merged[key] = dict(line)
    return list(merged.values())

def merged_mods(mods):
    """("pierce", 1) x 9 -> ("pierce", 9). Multiplying mods ("damage", 1.1) are multiplied."""
    from systems.mods import mod_combine
    merged = {}
    for name, value in mods:
        if name not in merged:
            merged[name] = value
        elif mod_combine(name) == "mul":
            merged[name] *= value
        else:
            merged[name] += value
    return list(merged.items())

def describe_bonuses(source, include_stats=True):
    """-> [str, ...] one line for everything this item / node gives."""
    from systems.mods import describe_mod
    from systems.status import describe_effect
    from systems.pets import pet_display_name
    lines = []
    if include_stats:
        lines += [describe_stat_line(line) for line in merged_stat_lines(get_part(source, "stats") or ())]
    for name, value in merged_mods(get_part(source, "mods") or ()):
        lines.append(describe_mod(name, value))
    for name, value in (get_part(source, "grants") or {}).items():
        lines.append(grant_label(name) if value is True else f"+{value:g} {grant_label(name).lower()}")
    for event, effects in (get_part(source, "effects") or {}).items():
        when = event.replace("_", " ")                       # "on_kill" -> "on kill"
        for effect in effects:
            lines.append(f"{describe_effect(effect)} ({when})")
    for pet_type, count in (get_part(source, "summons") or {}).items():
        lines.append(f"Summons {count} {pet_display_name(pet_type, count)}")
    return lines


# ---------------------------------------------------------------
# START-UP CHECK - used by check_all_content() in systems/tags.py
# ---------------------------------------------------------------
def check_bonuses(where, source, problems):
    """Add a line to `problems` for every unknown stat, mod, effect or pet."""
    from systems.items import stat_defs
    from systems.mods import mod_types
    from systems.status import status_effect_types, hit_effect_types
    from systems.pets import pet_configs
    for line in get_part(source, "stats") or ():
        if line.get("stat") not in stat_defs:
            problems.append(f"{where}: unknown stat '{line.get('stat')}'")
        if line.get("type") not in ("flat", "increased"):
            problems.append(f"{where}: stat '{line.get('stat')}' needs \"type\": \"flat\" or \"increased\"")
    for name, _ in get_part(source, "mods") or ():
        if name not in mod_types:
            problems.append(f"{where}: unknown mod '{name}'")
    for event, effects in (get_part(source, "effects") or {}).items():
        for effect in effects:
            if effect.get("name") not in status_effect_types and effect.get("name") not in hit_effect_types:
                problems.append(f"{where}: unknown effect '{effect.get('name')}'")
    for pet_type in get_part(source, "summons") or {}:
        if pet_type not in pet_configs:
            problems.append(f"{where}: summons unknown pet '{pet_type}'")
