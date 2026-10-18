"""Burn and poison: ailments a HIT can cause, based on the attacker's stats.

How it works:
  1. A hit lands (apply_player_hit in systems/enemies.py calls try_ailments).
  2. For each ailment, roll its chance:  attacker's "<ailment>_chance" + the hit's own.
  3. If it lands, the ailment's apply function puts it on the target as a normal
     status, so it is drawn above the target and ticks like every other status.

Every number is a normal STAT, so items, the passive tree, gem trees, supports
and pets can all change it:
  - player:  register_stat("burn_chance") etc.   (items / passive tree)
  - pets:    register_pet_stat("burn_chance")    (+ "pet_burn_chance" for the player)
  - a gem:   "burn_chance": 5 in its template, or a gem tree node / support gem
             using the "burn_chance" mod (systems/mods.py)

What a TARGET can resist is read from the target itself, so an enemy only needs
e.g. "immune": {"poison"} in its config. The player gets the defaults.

A new ailment = one entry in ailment_stats + a register_ailment() call at the bottom.
"""
import random
from systems.status import register_status
from systems.items import register_stat, panel_rows
from systems.pets import register_pet_stat

# ---------------------------------------------------------------
# STATS - each one becomes a player stat AND a pet stat.
#   key     the stat name items / the tree / gems use
#   label   name on items, e.g. "+5% Chance to Burn"
#   base    starting value
#   percent shown with % on items
#   text    how the stats panel and gem tooltips show it. {} = the number
# ---------------------------------------------------------------
ailment_stats = [
    ("burn_chance",       "Chance to Burn",          0,   True,  "Chance to burn: {}%"),
    ("burn_damage",       "Burn Damage",             5,   True,  "Burn damage: {}% of fire hit"),
    ("burn_duration",     "Burn Duration",           3,   False, "Burn duration: {}s"),

    ("poison_chance",     "Chance to Poison",        0,   True,  "Chance to poison: {}%"),
    ("poison_damage",     "Poison Damage per Stack", 0.1, True,  "Poison damage per stack: {}% max health/s"),
    ("poison_max_stacks", "Maximum Poison Stacks",   20,  False, "Max poison stacks: {}"),
    ("poison_duration",   "Poison Duration",         3,   False, "Poison duration: {}s"),
]

for key, label, base, percent, text in ailment_stats:
    register_stat(key, label, base=base, percent=percent, show_in_panel=False)   # the panel uses ailment_panel_rows below
    register_pet_stat(key, label, default=base, percent=percent, player_base=0)

def ailment_text(text, value):
    """"Burn damage: {}% of fire hit" + 5.0 -> "Burn damage: 5% of fire hit"."""
    return text.format(f"{round(value, 2):g}")

@panel_rows("offence")
def ailment_panel_rows(player):
    return [(ailment_text(text, getattr(player, key, 0)), (255, 255, 255))
            for key, label, base, percent, text in ailment_stats if getattr(player, key, 0)]

poison_tick_interval = 0.5          # poison deals its damage this often (seconds)

# An ailment only lands if the hit DEALT at least this much of the damage types that
# can cause it (after crit, resistance and protection). Burn needs fire, poison needs
# nature - set per ailment with register_ailment(..., types=...) at the bottom.
ailment_min_damage = 1

# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------
def attacker_value(attacker, stat, hit_stats=None):
    """The attacker's value of a stat PLUS what the hit itself carries (from the gem,
    its tree or a support). Works for the player and for pets."""
    hit_stats = hit_stats or {}
    if hasattr(attacker, "resolve_stat") and stat in getattr(attacker, "base_stats", ()):
        return attacker.resolve_stat(stat, hit_stats)              # the player: (base + flat) * increased
    own = attacker.get_stat(stat, 0) if hasattr(attacker, "get_stat") else 0   # a pet
    return own + hit_stats.get(stat, 0)

def target_value(target, key, default):
    """What the TARGET says about an ailment, e.g. "poison_stack_mult". Missing = default."""
    return getattr(target, key, default)

def deal_damage(target, amount, flash=False, source=None):     # ticks don't flash, or it would stay red
    if hasattr(target, "enemy_take_damage"):
        target.enemy_take_damage(amount, flash=flash, source=source)
    else:
        target.take_damage(amount, flash=flash)

def ailment_source(attacker, hit_stats, origin):
    """What a burn / poison deals its damage AS: it remembers the hit's on-kill
    effects, so a fireball's burn that kills triggers the fireball's on-kill."""
    from systems.status import EffectSource
    return EffectSource(0, {"on_kill": (hit_stats or {}).get("on_kill", ())}, 0, attacker=attacker, origin=origin)

# ---------------------------------------------------------------
# BURN - ONE burn. A new burn always REPLACES the old one, even a weaker one.
#   damage per second = burn_damage % of the hit's fire damage (or every type that
#   can burn) BEFORE the target's defences, but after crit.
#   The burn deals FIRE damage: each tick is reduced by fire resistance (never protection).
# ---------------------------------------------------------------
def apply_burn(target, attacker, hit_stats, landed_parts, raw_parts=None):
    base = ailment_damage("burn", hit_stats, raw_parts or landed_parts, attacker)
    duration = attacker_value(attacker, "burn_duration", hit_stats) * target_value(target, "burn_duration_mult", 1.0)
    if duration <= 0:
        return
    target.statuses["burn"] = {
        "remaining": duration,
        "dps": base * attacker_value(attacker, "burn_damage", hit_stats) / 100,
        "attacker": attacker,                                      # its penetration is used
        "source": ailment_source(attacker, hit_stats, "burn"),
    }

def burn_tick(target, status, dt):
    damage = ailment_hit(target, "burn", status["dps"] * dt, status.get("attacker"))
    deal_damage(target, damage, source=status.get("source"))

# ---------------------------------------------------------------
# POISON - ONE poison with STACKS.
#   every hit that poisons adds 1 stack and refreshes the timer of ALL stacks
#   damage every tick = stacks * poison_damage % of the target's max health
#   the poison always uses the BEST poison_damage / max stacks of everyone who
#   poisoned it while it was active (so one player hit upgrades the pets' stacks)
# ---------------------------------------------------------------
def apply_poison(target, attacker, hit_stats, landed_parts, raw_parts=None):
    max_stacks = attacker_value(attacker, "poison_max_stacks", hit_stats) * target_value(target, "poison_stack_mult", 1.0)
    duration = attacker_value(attacker, "poison_duration", hit_stats) * target_value(target, "poison_duration_mult", 1.0)
    percent = attacker_value(attacker, "poison_damage", hit_stats)
    if max_stacks < 1 or duration <= 0:
        return

    poison = target.statuses.get("poison")
    if poison is None:
        poison = {"stacks": 0, "remaining": 0, "percent": 0, "max_stacks": 0,
                  "tick_timer": poison_tick_interval, "attacker": attacker}
        target.statuses["poison"] = poison

    if percent > poison["percent"]:
        poison["percent"] = percent
        poison["attacker"] = attacker                              # its penetration is used
    poison["max_stacks"] = max(poison["max_stacks"], int(max_stacks))
    poison["stacks"] = min(poison["stacks"] + 1, poison["max_stacks"])
    poison["remaining"] = max(poison["remaining"], duration)       # refresh the whole stack
    poison["source"] = ailment_source(attacker, hit_stats, "poison")   # the LAST hit that poisoned gets the kill

def poison_tick(target, status, dt):
    status["tick_timer"] -= dt
    while status["tick_timer"] <= 0:
        status["tick_timer"] += poison_tick_interval
        damage = status["stacks"] * status["percent"] / 100 * target.max_health * poison_tick_interval   # % per SECOND
        damage = ailment_hit(target, "poison", damage, status["attacker"])
        deal_damage(target, damage, source=status.get("source"))


# ---------------------------------------------------------------
# REGISTRY
# ---------------------------------------------------------------
ailment_types = {}

def register_ailment(name, apply, tick, label, color, describe=None, avoid_label=None, types=(),
                     damage_type=None):
    """name     also the status name, and the start of its stats: "<name>_chance"
    types    the damage types that can CAUSE it: ("nature",). The hit must DEAL at least
             ailment_min_damage of them. More types can be allowed:
               on a gem / support hit:  "poison_types": ["physical"]  (or "all")
               on an item / tree node:  "grants": {"all_damage_can_poison": True}
             () = any damage can cause it.
    damage_type  the type it DEALS, whatever caused it: "fire" for burn, "nature" for poison.
             Each tick is reduced by the target's resistance to it (never protection).
    apply    apply(target, attacker, hit_stats, landed_parts) - puts it on the target
    tick     tick(target, status, dt) - every frame while active
    label    text above the target. A function gets the status: lambda s: f"Poison x{s['stacks']}"
    A target with the name in its "immune" set never gets it."""
    ailment_types[name] = {"apply": apply, "types": tuple(types), "damage_type": damage_type}
    from systems.bonuses import register_grant_label
    register_grant_label(f"all_damage_can_{name}", f"All damage can {name}")
    register_status(name, tick=tick, label=label, color=color, describe=describe, avoid_label=avoid_label)

def ailment_types_for(name, hit_stats, attacker=None):
    """The damage types that can cause this ailment on this hit, or None = every type.
    Its own types + what the hit allows ("poison_types") + "all_damage_can_poison"."""
    extra = (hit_stats or {}).get(f"{name}_types", ())
    extra = [extra] if isinstance(extra, str) else list(extra)
    if "all" in extra or not ailment_types[name]["types"]:
        return None
    if hasattr(attacker, "has_grant") and attacker.has_grant(f"all_damage_can_{name}"):
        return None
    return set(ailment_types[name]["types"]) | set(extra)

def ailment_damage(name, hit_stats, parts, attacker=None):
    """How much of `parts` ({"fire": 80, ...}) counts for this ailment."""
    types = ailment_types_for(name, hit_stats, attacker)
    if types is None:
        return sum(parts.values())                                 # every type counts
    return sum(parts.get(t, 0) for t in types)

def ailment_hit(target, name, amount, attacker):
    """One tick of an ailment's damage, as its OWN damage type ("fire" / "nature"):
    reduced by the target's resistance to it, never by protection."""
    damage_type = ailment_types[name]["damage_type"]
    if not damage_type:
        return amount
    from systems.damage import resolve_damage
    return resolve_damage(amount, {"damage_type": damage_type}, target, attacker, protectable=False)

def try_ailments(target, attacker, hit_stats, landed_parts, raw_parts=None):
    """Called once for every hit that lands.
    landed_parts  the damage per type the hit DEALT (after crit, resistance and protection)
    raw_parts     the same BEFORE the target's defences (burn is worked out from this)"""
    from systems.status import avoids
    for name, ailment in ailment_types.items():
        if ailment_damage(name, hit_stats, landed_parts, attacker) < ailment_min_damage:
            continue                                               # not enough of its damage type got through
        chance = attacker_value(attacker, f"{name}_chance", hit_stats)
        if chance > 0 and random.uniform(0, 100) < chance and not avoids(target, name):
            ailment["apply"](target, attacker, hit_stats, landed_parts, raw_parts or landed_parts)

register_ailment("burn", apply_burn, burn_tick, label="Burning", color=(255, 120, 60), avoid_label="Being Burned",
                 types=("fire",), damage_type="fire")
register_ailment("poison", apply_poison, poison_tick, label=lambda s: f"Poison x{s['stacks']}", color=(110, 220, 90), avoid_label="Being Poisoned",
                 types=("nature",), damage_type="nature")