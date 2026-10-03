import random

from systems.rarity import monster_tier_max, monster_tier_min

# region Monster tier and rank


# Two separate things sit on every monster:
#
#   TIER  0-10   how deep in the game it is. Scales its base stats, and
#                limits how good the mods on its drops may be.
#   RANK         normal / uncommon / rare / epic / legendary. Decides how
#                MANY and how GOOD items it drops, and may buff it further.
#
# An area has a tier; the monsters in it are built from that.
# Nothing here names a specific monster - content fills the registries.

# ---------------------------------------------------------------
# TIER -> STATS
#
# Three levels decide a monster's stat at a given tier. The most specific
# one that exists wins, so you only write what you actually want to control:
#
#   1. "tier_stats" on the monster   exact value at that exact tier
#   2. "tier_scaling" on the monster its own curve: base * factor ** tier
#   3. tier_stat_scaling below       the fallback curve for every monster
#
# EVERY stat is MULTIPLIED, so for a TIMER a factor BELOW 1.0 is what makes
# the monster faster. 0.95 means 5% quicker per tier, 1.0 means unchanged.
# ---------------------------------------------------------------
tier_stat_scaling = {
    "health":         1.55,
    "contact_damage": 1.35,
    "xp_value":       1.50,

    # timers - below 1.0 = faster. Left at 1.0 so nothing changes until you
    # decide a monster should speed up with tier.
    "cast_time":      1.0,     # wind-up before a spell lands
    "cast_cooldown":  1.0,     # pause after any cast

    # the monster's abilities (see tier_ability_stats below)
    "ability_damage":   1.40,
    "ability_cooldown": 1.0,
    "ability_projectiles": 1.0,     # 1.0 = always one shot
}

# A timer must never reach zero, or the monster casts every single frame.
# Scaled values are clamped to these, and so are exact tier_stats values.
tier_stat_floor = {
    "cast_time":        0.05,
    "cast_cooldown":    0.05,
    "ability_cooldown": 0.15,
}

# Abilities are separate objects, so they get their own names.
#   stat name on the monster -> attribute on each of its abilities
# Add a line here and that attribute scales too (ability_range, aoe, speed...).
tier_ability_stats = {
    "ability_damage":      "damage",
    "ability_cooldown":    "cooldown",
    "ability_projectiles": "projectiles",
}

# Stats that must land on a whole number (never 2.07 projectiles).
tier_stat_integer = {"ability_projectiles"}

def tier_value(stat, value):
    """Clamp a scaled stat: never below its floor, and whole if it is a count."""
    floor = tier_stat_floor.get(stat)
    if floor is not None:
        value = max(floor, value)
    if stat in tier_stat_integer:
        value = max(1, int(round(value)))
    return value

def tier_curve_factor(enemy, stat):
    own = getattr(enemy, "tier_scaling", None) or {}
    if stat in own:
        return own[stat]
    return tier_stat_scaling.get(stat, 1.0)

def exact_tier_stats(enemy, tier):
    """The exact values that apply at this tier.

    By default a row applies to ITS tier only, so tier 6 goes back to the
    curve. With "tier_stats_sticky": True a row applies from its tier
    upwards until the next row, which is usually what you want for a
    hand-tuned monster ("3 projectiles from tier 5 on").
    """
    table = getattr(enemy, "tier_stats", None) or {}
    if not table:
        return {}
    if not getattr(enemy, "tier_stats_sticky", False):
        return table.get(tier, {})
    rows = sorted(t for t in table if t <= tier)
    merged = {}
    for t in rows:                     # later rows overwrite earlier ones
        merged.update(table[t])
    return merged

def apply_monster_tier(enemy):
    """Scale a freshly created monster by its own .tier. Runs once."""
    tier = getattr(enemy, "tier", 1)
    exact = exact_tier_stats(enemy, tier)
    own = getattr(enemy, "tier_scaling", None) or {}

    # --- stats that live on the monster itself ---------------------------
    scalable = set(tier_stat_scaling) | set(own) | set(exact)
    scalable -= set(tier_ability_stats)
    scalable -= {f"{name}_mult" for name in tier_ability_stats}

    for stat in scalable:
        if not hasattr(enemy, stat):
            if stat in own or stat in exact:
                warn_once(f"monster '{enemy.enemy_type}': '{stat}' is not a stat on a monster."
                          f" Ability stats need the ability_ prefix (ability_projectiles).")
            continue
        if stat in exact:
            setattr(enemy, stat, tier_value(stat, exact[stat]))
            continue
        if tier <= 0:
            continue
        factor = tier_curve_factor(enemy, stat)
        if factor != 1.0:
            setattr(enemy, stat, tier_value(stat, getattr(enemy, stat) * factor ** tier))

    enemy.max_health = enemy.health

    # --- stats that live on each of its abilities -------------------------
    for stat, attribute in tier_ability_stats.items():
        if f"{stat}_mult" in exact:
            mult = exact[f"{stat}_mult"]
        elif tier > 0:
            mult = tier_curve_factor(enemy, stat) ** tier
        else:
            mult = 1.0
        if mult == 1.0:
            continue
        for ability in getattr(enemy, "abilities", ()):
            if hasattr(ability, attribute):
                setattr(ability, attribute, tier_value(stat, getattr(ability, attribute) * mult))

# ---------------------------------------------------------------
# RANK -> DROPS (and optionally more stats)
#
#   register_monster_rank("rare", weight=8, drop_count=(3, 5),
#                         stat_mult={"health": 4}, rarity_weights={...})
#
#   weight          how often it is rolled, against the other ranks
#   drop_count      how many items it drops, on top of its drop pool's own roll
#   stat_mult       multiplies the monster's stats, after tier scaling
#   rarity_weights  biases the rarity of items it drops (None = normal odds)
#   label / color   for the health bar or name plate later
#   apply           your own function(enemy) for anything else
# ---------------------------------------------------------------
default_rank = "normal"
monster_ranks = {}

def register_monster_rank(name, weight=1, drop_count=(0, 0), stat_mult=None,
                          ability_mult=None, rarity_weights=None, drop_tier_bonus=0,
                          label=None, color=None, apply=None, **settings):
    monster_ranks[name] = {
        "weight": weight,
        "drop_count": drop_count,
        "stat_mult": stat_mult or {},
        "ability_mult": ability_mult or {},
        "rarity_weights": rarity_weights,
        "drop_tier_bonus": drop_tier_bonus,
        "label": label or name.title(),
        "color": color,
        "apply": apply,
        **settings,
    }
    return name

def roll_monster_rank(extra_weights=None, only=None):
    """extra_weights changes some odds and keeps the rest.
    only replaces the whole list, so nothing outside it can be rolled."""
    if only:
        weights = dict(only)
    else:
        weights = {name: cfg["weight"] for name, cfg in monster_ranks.items()}
        if extra_weights:
            weights.update(extra_weights)
    names = [n for n, w in weights.items() if w > 0]
    if not names:
        return default_rank
    return random.choices(names, weights=[weights[n] for n in names], k=1)[0]

def apply_monster_rank(enemy):
    """Apply the rank's stat bonuses and its own apply(). Runs once, after tier."""
    config = monster_ranks.get(getattr(enemy, "rank", default_rank))
    if not config:
        return
    for stat, mult in config["stat_mult"].items():
        if hasattr(enemy, stat):
            setattr(enemy, stat, tier_value(stat, getattr(enemy, stat) * mult))
    if "health" in config["stat_mult"]:
        enemy.max_health = enemy.health
    # the same, for attributes that live on its abilities (damage, cooldown...)
    for attribute, mult in config["ability_mult"].items():
        floor_key = next((s for s, a in tier_ability_stats.items() if a == attribute), None)
        for ability in getattr(enemy, "abilities", ()):
            if hasattr(ability, attribute):
                value = getattr(ability, attribute) * mult
                setattr(ability, attribute, tier_value(floor_key, value) if floor_key else value)
    if config["apply"]:
        config["apply"](enemy)

def rank_drop_count(rank):
    """Extra rolls this rank adds. Written the same two ways as a pool's
    drop_count: (1, 2) for even odds, or {1: 75, 2: 25} for your own."""
    from systems.drops import roll_drop_count
    config = monster_ranks.get(rank)
    if not config:
        return 0
    return roll_drop_count(config["drop_count"])

def rank_drop_tier_bonus(rank):
    """How many tiers this rank adds when deciding how good its loot may be."""
    config = monster_ranks.get(rank)
    return config.get("drop_tier_bonus", 0) if config else 0

def rank_label(rank):
    config = monster_ranks.get(rank)
    return config["label"] if config else ""

def rank_color(rank):
    config = monster_ranks.get(rank)
    return config["color"] if config else None

def build_monster(enemy, tier=0, rank=None, extra_rank_weights=None, rank_only=None):
    """Give a new monster its tier and rank, then apply both. One call."""
    enemy.tier = max(monster_tier_min, min(monster_tier_max, tier))
    enemy.rank = rank or roll_monster_rank(extra_rank_weights, only=rank_only)
    apply_monster_tier(enemy)
    apply_monster_rank(enemy)
    return enemy
#endregion