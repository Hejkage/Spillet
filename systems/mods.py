import random

# region Mods - ONE name for every bonus, written the same everywhere
#
# A MOD is a (name, value) pair:   ("max_health", 50)   ("increased_fire_damage", 10)   ("pierce", 1)
#
# The SAME list works on every source:
#
#     an item / unique         mods=[("max_health", 50), ("pierce", 1)]
#     a passive tree node      mods=[...]   or per_point={"mods": [...]}
#     a gem tree node          mods=[...]
#     a pet tree node          mods=[...]
#     a support gem            register_support_gem(..., mod="pierce")
#     a gem that always has it "always": [("pierce", 3)]   in content/gems.py
#
# WHERE IT SITS decides who gets it:
#     item / passive tree  -> you, and every ability it fits
#     gem tree / support   -> only that one gem
#     pet tree             -> only that one pet
#
# THE NAME SAYS WHAT KIND OF BONUS IT IS:
#     <stat>             FLAT: adds to the stat           ("max_health", 50)
#     increased_<stat>   INCREASED: % - every increased bonus to the same
#                        stat is ADDED first, then applied once     ("increased_max_health", 10)
#     more_<thing>       MORE: % - each one multiplies on its own   ("more_damage", 12)
#     anything else      a mechanic                        ("pierce", 1)  ("split", 4)
#
# Every stat registered with register_stat() (systems/items.py) or
# register_pet_stat() (systems/pets.py) gets its two names automatically -
# a new stat needs nothing here.
#
# STATS ON ONE GEM: a gem tree or support only takes stats that a single hit
# can use (crit, penetration, increased fire damage, burn chance...). Putting
# "max_health" on a fireball tree is an error at start-up instead of doing nothing.
#
# NEEDS decide where a mod may land on an ability (tags: systems/tags.py).
# SCALES is the damage a mod adds ("added_fire" scales {"fire"}): an ability
# that has it in "blocked" refuses the mod.

mod_types = {}          # the mods registered by hand: mechanics, more_..., effects

def register_mod(name, apply, needs=None, scales=None, describe=None, combine="add"):
    """apply(packets, value) -> packets
    needs     tags the ability must ALL have: {"projectile"}, {"melee"}, {"damage", "spell"}...
    scales    damage types it adds, e.g. {"fire"}. An ability that blocks them refuses it.
    describe  describe(value) -> the line shown in tooltips
    combine   how two of the same add up: "add", or "more" (each multiplies)
    """
    mod_types[name] = {
        "apply": apply,
        "needs": set(needs or ()),
        "scales": set(scales or ()),
        "describe": describe,
        "combine": combine,
        "stat": None,
    }
    return name

# ---------------------------------------------------------------
# STAT MODS - made from the stat registry, so every stat has a name
# ---------------------------------------------------------------
def stat_of(name):
    """("max_health" -> ("max_health", "flat"), "increased_max_health" -> ("max_health", "increased"),
    None if the name is not a player stat."""
    from systems.items import stat_defs
    if name in stat_defs:
        return name, "flat"
    if name.startswith("increased_") and name[len("increased_"):] in stat_defs:
        return name[len("increased_"):], "increased"
    return None

def pet_stat_of(name):
    """The same for a pet's own stats ("increased_damage" -> ("damage", "increased"))."""
    from systems.pets import pet_stat_defs
    if name in pet_stat_defs:
        return name, "flat"
    if name.startswith("increased_") and name[len("increased_"):] in pet_stat_defs:
        return name[len("increased_"):], "increased"
    return None

def hit_stat_needs(stat):
    """The tags a stat needs to work on ONE hit, or None if a single hit can't use it
    (max_health, movement_speed, resistances...). Only these may go on a gem tree / support."""
    from systems.damage import damage_types, damage_keys, flat_conditions
    from systems.ailments import ailment_stats
    if stat in ("damage", "crit_chance", "crit_damage"):
        return {"damage"}
    if stat in ("attack_crit_chance", "attack_speed", "lifesteal"):
        return {"attack"}
    if stat in ("spell_crit_chance", "cooldown", "spell_leech", "spell_leech_to_mana"):
        return {"spell"}
    if stat == "projectile_speed":
        return {"projectile"}
    if stat == "aoe":
        return {"aoe"}
    if stat in {key for key, *_ in ailment_stats}:
        return {"damage"}
    for key in damage_keys:
        if stat in (f"{key}_damage", f"{key}_penetration", f"{key}_protection_penetration"):
            return {"damage", key} if key in flat_conditions else {"damage"}
    for t in damage_types:
        if stat == f"added_{t}":
            return {"damage"}
        for condition in flat_conditions:
            if stat == f"added_{t}_{condition}":
                return {"damage", condition}
    return None

# A hit packet already has its own "damage", "aoe" and "speed" numbers. A FLAT stat
# with one of those names is stored under "<stat>_flat" on a hit, so the two never mix.
packet_fields = {"damage", "aoe", "speed"}

def hit_key(stat):
    """Where a flat stat lives on a hit packet ("crit_chance" -> "crit_chance", "damage" -> "damage_flat")."""
    return stat + "_flat" if stat in packet_fields else stat

def _stat_mod(name):
    """A mod entry for a stat name, made the first time it is asked for."""
    found = stat_of(name)
    if found is None:
        return None
    stat, kind = found
    from systems.damage import damage_types
    needs = hit_stat_needs(stat)
    scales = {t for t in damage_types if stat == f"added_{t}" or stat.startswith(f"added_{t}_")}
    key = hit_key(stat) if kind == "flat" else stat + "_increase"     # what player.resolve_stat() reads on a hit
    def describe(value, stat=stat, kind=kind):
        from systems.bonuses import describe_stat_line
        return describe_stat_line({"stat": stat, "type": kind, "amount": value})
    return {"apply": add_key(key), "needs": needs or set(), "scales": scales, "describe": describe,
            "combine": "add", "stat": (stat, kind), "hit": needs is not None}

def get_mod(name):
    """Everything about a mod name, or None if it doesn't exist."""
    if name in mod_types:
        return mod_types[name]
    return _stat_mod(name)

def mod_exists(name):
    return get_mod(name) is not None

def is_stat_mod(name):
    mod = get_mod(name)
    return bool(mod and mod["stat"])

def works_on_one_hit(name):
    """Can this mod go on a gem tree / support gem (= change one gem's hits)?"""
    mod = get_mod(name)
    return mod is not None and (not mod["stat"] or mod["hit"])

def owner_mod_problem(name, owner):
    """Why this mod can't go on a source owned by `owner` ("player", "gem", "pet"), or None."""
    if owner == "pet":
        return None if pet_stat_of(name) else f"'{name}' is not a pet stat (see register_pet_stat in systems/pets.py)"
    if not mod_exists(name):
        return f"unknown mod '{name}'"
    if owner == "gem" and not works_on_one_hit(name):
        return f"'{name}' can't go on one gem - a single hit can't use it (it belongs on items or the passive tree)"
    return None

def mod_allowed(name, ability_tags, blocked=()):
    """True if this mod may land on an ability with these tags / blocked set."""
    from systems.tags import fits
    mod = get_mod(name)
    if mod is None:
        return False
    return fits(mod["needs"], mod["scales"], ability_tags, blocked)

def apply_mod(name, packets, value):
    mod = get_mod(name)
    if mod is None:
        print(f"WARNING: mod '{name}' is not registered. See systems/mods.py.")
        return packets
    return mod["apply"](packets, value)

def apply_mods(packets, mods, ability_tags=None, blocked=()):
    """mods = [(name, value), ...] applied in order.
    ability_tags=None means "no filtering" (a gem's own `always` list and its
    own tree, which the author chose deliberately)."""
    for name, value in mods or ():
        if ability_tags is not None and not mod_allowed(name, ability_tags, blocked):
            continue
        packets = apply_mod(name, packets, value)
    return packets

def describe_mod(name, value):
    mod = get_mod(name)
    if mod and mod["describe"]:
        return mod["describe"](value)
    return f"{name} {value}"

def mod_needs(name):
    mod = get_mod(name)
    return mod["needs"] if mod else set()

def mod_scales(name):
    mod = get_mod(name)
    return mod["scales"] if mod else set()

def mod_combine(name):
    mod = get_mod(name)
    return mod["combine"] if mod else "add"

def combine_values(name, values):
    """Several of the same mod as one number: "add" adds, "more" multiplies
    (10% more and 10% more = 21% more). Effect mods with a dict value keep the first."""
    values = list(values)
    if not values:
        return 0
    if mod_combine(name) == "more":
        total = 1.0
        for v in values:
            total *= 1 + v / 100
        return round((total - 1) * 100, 3)
    return sum(values)

# ---------------------------------------------------------------
# LAYING OUT PACKETS
# ---------------------------------------------------------------
spread_angle = 15        # degrees between projectiles in an even fan

def spread_packets(base, count):
    """Turn one packet into `count` of them: a random cone if the packet asks
    for one, otherwise an even fan."""
    base_dir = base["base_direction"]
    cone = base.get("cone_angle")
    if cone:
        return [{**base, "direction": base_dir.rotate(random.uniform(-cone / 2, cone / 2))}
                for _ in range(count)]
    if count <= 1:
        return [base]
    start = -(count - 1) / 2
    return [{**base, "direction": base_dir.rotate((start + i) * spread_angle)}
            for i in range(count)]

# ---------------------------------------------------------------
# BUILDING BLOCKS - each mechanic exists in ONE place
# ---------------------------------------------------------------
def add_key(key, to_int=False):
    """Build a mod that adds to one field on every packet."""
    def apply(packets, value):
        for p in packets:
            p[key] = p.get(key, 0) + (int(value) if to_int else value)
        return packets
    return apply

def more_key(key, start=None):
    """Build a MORE mod: multiplies one field by (1 + value%). start = the field's
    value when the packet doesn't have it yet (None: leave a missing field alone)."""
    def apply(packets, value):
        for p in packets:
            if key in p or start is not None:
                p[key] = p.get(key, start) * (1 + value / 100)
        return packets
    return apply

def more_text(value, label):
    """12 -> "12% more damage", -10 -> "10% less damage"."""
    value = round(value, 1)
    return f"{value:g}% more {label}" if value >= 0 else f"{-value:g}% less {label}"

def add_projectiles(packets, value):
    return spread_packets(packets[0], len(packets) + int(value))

def set_orbit(packets, value):
    for p in packets:
        p["orbit"] = True
        p["orbit_radius"] = p.get("orbit_radius", 0) + value
    return packets

def burst_fire(packets, value):
    extra = int(value)
    cooldown_mult = 1.5 + (extra - 1) * 0.25
    for p in packets:
        p["cooldown_mult"] = p.get("cooldown_mult", 1.0) * cooldown_mult
        p["burst_extra"] = p.get("burst_extra", 0) + extra
        p["burst_interval"] = 0.05
    return packets

# ---------------------------------------------------------------
# EFFECT MODS - put an effect (systems/status.py) on a hit
#
#   event "on_hit"   it happens to what the hit hits
#   event "on_kill"  it happens when the hit kills (centred on the dead enemy)
#
# The mod's value goes into one field of the effect (value_field), so the same
# mod can be rolled at different strengths. Two of the same mod on one gem
# STACK into one bigger effect (two "fire_explosion 20" = one at 40).
# ---------------------------------------------------------------
def add_effect(name, event="on_hit", value_field=None, stack=True, **defaults):
    field = "effects" if event == "on_hit" else event
    def apply(packets, value):
        for p in packets:
            effects = list(p.get(field, ()))
            same = [i for i, e in enumerate(effects) if e["name"] == name] if (stack and value_field) else []
            if same:
                old = effects[same[0]]
                effects[same[0]] = {**old, value_field: old.get(value_field, 0) + value}
            else:
                effect = {"name": name, **defaults}
                if value_field:
                    effect[value_field] = value
                effects.append(effect)
            p[field] = effects
        return packets
    return apply

def register_effect_mod(name, effect, value_field, event="on_hit", needs=("damage",), stack=True):
    """A named mod that attaches an effect. Use it from content/:

        register_effect_mod("fire_explosion",
                            {"name": "explode", "type": "fire", "of": "hit", "radius": 150},
                            value_field="percent")

    Then ("fire_explosion", 30) works on items, trees and support gems alike."""
    effect = dict(effect)
    effect_name = effect.pop("name")
    def describe(value):
        from systems.status import describe_effect
        when = "" if event == "on_hit" else f" ({event.replace('_', ' ')})"
        return describe_effect({"name": effect_name, **effect, value_field: value}) + when
    return register_mod(name, add_effect(effect_name, event, value_field, stack, **effect),
                        needs=needs, describe=describe)

# ---------------------------------------------------------------
# THE MECHANICS - registered by hand. Stats need nothing here.
# ---------------------------------------------------------------
# --- MORE: each one multiplies on its own ---------------------------------
register_mod("more_damage", more_key("damage_more", start=1.0), needs={"damage"}, combine="more",
             describe=lambda v: more_text(v, "damage"))
register_mod("more_aoe", more_key("aoe"), needs={"aoe"}, combine="more",
             describe=lambda v: more_text(v, "area of effect"))
register_mod("more_dot_damage", more_key("dot_damage"), needs={"dot"}, combine="more",
             describe=lambda v: more_text(v, "damage over time"))
register_mod("more_projectile_speed", more_key("speed"), needs={"projectile"}, combine="more",
             describe=lambda v: more_text(v, "projectile speed"))
register_mod("more_reach", more_key("range_mult", start=1.0), needs={"melee"}, combine="more",
             describe=lambda v: more_text(v, "swing reach"))

# --- projectiles ----------------------------------------------------------
register_mod("projectiles", add_projectiles, needs={"projectile"},
             describe=lambda v: f"+{int(v)} projectiles")
register_mod("pierce", add_key("pierce", to_int=True), needs={"projectile"},
             describe=lambda v: f"Pierces {int(v)} more targets")
register_mod("burst", burst_fire, needs={"projectile"},
             describe=lambda v: f"Fires {int(v)} extra times")
register_mod("orbit", set_orbit, needs={"projectile"},
             describe=lambda v: f"Orbits you at {int(v)} range")
register_mod("split", add_effect("split", damage_mult=0.25, size_mult=0.6, value_field="count"),
             needs={"projectile"},
             describe=lambda v: f"On hit, fires {int(v)} smaller projectiles in a circle (25% damage)")
def set_return(packets, value):
    """Two return mods: the shortest time wins."""
    for p in packets:
        p["return_after"] = min(p["return_after"], value) if p.get("return_after") else value
    return packets

register_mod("return", set_return, needs={"projectile"},
             describe=lambda v: f"Returns to you after {v:g}s, or when it hits a wall")
register_mod("chain", add_effect("chain", damage_mult=0.8, range=400, value_field="count"),
             needs={"projectile"},
             describe=lambda v: f"Chains to {int(v)} more enemies (-20% damage per chain)")

# --- melee ----------------------------------------------------------------
register_mod("arc", add_key("arc"), needs={"melee"},
             describe=lambda v: f"+{int(v)} degree swing arc")
register_mod("max_targets", add_key("max_targets", to_int=True), needs={"melee"},
             describe=lambda v: f"+{int(v)} targets hit")
#endregion
