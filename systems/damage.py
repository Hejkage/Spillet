"""Damage types, tags, resistance, protection and penetration.

A hit has a SPLIT: how much of it is each damage type.
    {"fire": 40, "cold": 20, "nature": 30, "shadow": 10}
Each part is worked out on its own, using the part's KEYS: its damage type plus
the tags that go with it. A fire part is {"fire", "elemental"} plus the tags of
the whole hit ("spell" or "attack"). Resistance and protection (defender) and
penetration (attacker) are looked up per key, so one "elemental_penetration"
works on every elemental part and "spell_penetration" on every part of a spell.
"""

# Add a new damage type: ONE line here. Value = the tags it counts as.
damage_types = {
    "physical": (),
    "fire":     ("elemental",),
    "frost":    ("elemental",),
    "nature":   ("elemental",),
    "shadow":   ("dark",),
    "pure":     ("light",),
}

# Tags that are not damage types and not groups either.
# Both are added to a hit automatically from the gem.
extra_tags = ("attack", "spell")

default_damage_type = "physical"

# Colours for readouts (target dummy). A type with no entry is drawn white.
damage_colors = {
    "physical": (150, 0, 0),
    "fire":     (255, 120, 60),
    "frost":    (110, 200, 255),
    "nature":   (110, 220, 90),
    "shadow":   (170, 110, 230),
    "pure":     (255, 255, 150),
}

# "added_cold" adds flat cold to every hit that accepts it.
# "added_cold_spell" adds it to spells only. Add a tag here to get a new condition.
flat_conditions = ("spell", "attack")

max_resistance = 50      # % reduction of the hit
max_protection = 5000    # flat damage removed after resistance

# Groups the damage types belong to, e.g. "elemental". Found from the types above,
# so a new group is just a new tag on a type - there is no list to keep in step.
damage_groups = sorted({g for tags in damage_types.values() for g in tags})

# Every key a hit can be: its type, the groups that type is in, and attack/spell.
# Each one gets resistance, protection, penetration and increased-damage stats.
damage_keys = list(dict.fromkeys([*damage_types, *damage_groups, *extra_tags]))

def damage_split(hit_stats):
    """{"fire": 0.4, "cold": 0.2, ...}. The shares always add up to 1.
    A hit with only "damage_type" is 100% of that type."""
    hit_stats = hit_stats or {}
    split = hit_stats.get("damage_split")
    if split:
        total = sum(split.values())
        if total > 0:
            return {t: v / total for t, v in split.items() if v > 0}
    return {hit_stats.get("damage_type") or default_damage_type: 1.0}


def part_keys(damage_type, hit_stats):
    """The keys ONE part of a hit counts as, e.g. {"fire", "elemental", "spell"}."""
    hit_stats = hit_stats or {}
    keys = {damage_type, *damage_types.get(damage_type, ())}
    if hit_stats.get("crit_type"):
        keys.add(hit_stats["crit_type"])            # "spell" or "attack"
    keys |= set(hit_stats.get("damage_tags", ()))   # anything extra a gem adds
    return keys


def attacker_stat(attacker, stat, hit_stats):
    """A penetration value: the attacker's stat, plus anything on the hit.
    A per-type stat comes from the folded totals, so it already includes its groups."""
    totals = getattr(attacker, "damage_totals", None)
    if totals is not None and stat in totals:
        return totals[stat] + (hit_stats or {}).get(stat, 0)
    if attacker is not None and stat in getattr(attacker, "base_stats", ()):
        return attacker.resolve_stat(stat, hit_stats)
    return (hit_stats or {}).get(stat, 0)

def cannot_scale_keys(hit_stats):
    """What a hit refuses to scale with: its "cannot_scale" set, plus every type
    inside a blocked group. {"elemental"} -> {"elemental", "fire", "frost", "nature"}."""
    blocked = set((hit_stats or {}).get("cannot_scale", ()))
    for t, tags in damage_types.items():
        if blocked & set(tags):
            blocked.add(t)
    return blocked

def final_damage(base_damage, hit_stats, stat):
    """Work out what an ability really deals BEFORE the target is known.
    Used by gems, basic attacks and pets alike.

    base_damage  the ability's number, shared out by its damage_type/damage_split
    hit_stats    the ability's own fields: damage_type / damage_split, crit_type,
                 damage_tags, cannot_scale
    stat         stat(name, default) -> the attacker's value for that stat

    Returns (total, parts) where parts = {"fire": 100.0, "frost": 60.0}.
    Put `parts` in the hit as "damage_split"; resolve_damage() does the rest.

    1. FLAT: every "added_<type>" stat is added - any ability can get any type.
       "added_<type>_spell" / "_attack" only land on spells / attacks.
    2. INCREASED: each part is multiplied by the increased-damage stats of its
       OWN keys: its type, that type's groups, and the hit's attack/spell.
       Added fire on a sword swing is increased by fire, elemental and attack.

    "cannot_scale": {"fire"} turns both off for that key: no added fire, and
    no increased fire. A group blocks every type in it; "spell"/"attack"
    blocks the conditional flat stats and that increased stat.
    """
    hit_stats = hit_stats or {}
    blocked = cannot_scale_keys(hit_stats)
    parts = {t: base_damage * share for t, share in damage_split(hit_stats).items()}

    hit_tags = set(hit_stats.get("damage_tags", ()))
    if hit_stats.get("crit_type"):
        hit_tags.add(hit_stats["crit_type"])

    for t in damage_types:
        if t in blocked:
            continue
        flat = stat(f"added_{t}", 0)
        for condition in flat_conditions:
            if condition in hit_tags and condition not in blocked:
                flat += stat(f"added_{t}_{condition}", 0)
        if flat:
            parts[t] = parts.get(t, 0) + flat

    for t in parts:
        increased = sum((stat(f"{k}_damage", 100) - 100) / 100 for k in part_keys(t, hit_stats) if k not in blocked)
        parts[t] *= max(0, 1 + increased)

    return sum(parts.values()), parts

# The stats a group hands down to every type in it. "+2% elemental penetration"
# IS "+2% fire, +2% frost, +2% nature penetration", so the group keeps no number
# of its own and nobody has to add two rows together.
folded_suffixes = ("resistance", "protection", "penetration", "protection_penetration")

def fold_damage_stats(raw):
    """Add each group's value into every type in that group.

    raw(stat) -> the plain value of a stat, e.g. raw("elemental_penetration").
    Returns {"fire_resistance": 60, "fire_penetration": 2, "frost_penetration": 2, ...}.
    The player and enemies both keep this, so a hit only looks up its own type."""
    totals = {}
    for damage_type, groups in damage_types.items():
        for suffix in folded_suffixes:
            totals[f"{damage_type}_{suffix}"] = (raw(f"{damage_type}_{suffix}") + sum(raw(f"{g}_{suffix}") for g in groups))
    return totals

def resolve_damage_parts(damage, hit_stats, defender, attacker=None, protectable=True):
    """Like resolve_damage(), but keeps the types apart: {"fire": 50.0, "cold": 60.0}.

    protectable=False is for damage over time: it is only reduced by
    resistance, never by protection."""
    result = {}
    for damage_type, share in damage_split(hit_stats).items():
        part = damage * share
        keys = part_keys(damage_type, hit_stats)

        def defence(suffix):
            return defender.defence_stat(f"{damage_type}_{suffix}")    # already includes "elemental" etc.

        # the type's own value already includes its groups; the hit's tags
        # ("spell", "attack") are not damage types, so they are added here
        tag_keys = keys - {damage_type} - set(damage_types.get(damage_type, ()))

        def penetration(suffix):
            total = attacker_stat(attacker, f"{damage_type}_{suffix}", hit_stats)
            return total + sum(attacker_stat(attacker, f"{k}_{suffix}", hit_stats) for k in tag_keys)

        # 1. resistance: a % of this part. Capped, then penetration lowers it.
        resistance = min(max_resistance, defence("resistance"))
        if resistance > 0:
            resistance = max(0, resistance - penetration("penetration"))
        part *= 1 - resistance / 100

        # 2. protection: flat damage removed from what is left of this part.
        if protectable:
            protection = min(max_protection, defence("protection"))
            protection = max(0, protection - penetration("protection_penetration"))
            part = max(0, part - protection)

        result[damage_type] = result.get(damage_type, 0) + part
    return result


def resolve_damage(damage, hit_stats, defender, attacker=None, protectable=True):
    """The damage that actually lands, after resistance and protection."""
    return sum(resolve_damage_parts(damage, hit_stats, defender, attacker, protectable).values())

def damage_lines(parts):
    """Tooltip lines for a hit's damage, e.g. "Fire Damage: 70".
    A mixed hit gets its total first, then one line per type.
    Used by gem items, the hotbar and pets, so they always look the same."""
    white = (255, 255, 255)
    shown = [(t, v) for t, v in sorted(parts.items(), key=lambda kv: -kv[1]) if v > 0]
    if len(shown) == 1:
        t, v = shown[0]
        return [(f"{t.title()} Damage: {v:.0f}", damage_colors.get(t, white))]
    lines = [(f"Damage: {sum(v for _, v in shown):.0f}", white)] if shown else []
    for t, v in shown:
        lines.append((f"  {t.title()} Damage: {v:.0f}", damage_colors.get(t, white)))
    return lines