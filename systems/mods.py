import random

# region Mods - the bottom layer
#
# A MOD is one named thing that changes how a hit behaves, written once.
#
#     register_mod("pierce", add_pierce, tags={"projectile"})
#
# It is a plain function (packets, value) -> packets and knows nothing about
# gems, items or the skill tree.
#
# A HIT PACKET is one dict describing one hit: damage, aoe, direction, speed,
# sprite, plus anything the ability put in its `extra`. A projectile spawns
# from one packet; a melee swing reads one. So a mod works for every kind of
# ability, not just projectiles.
#
# FOUR THINGS can name a mod, and none of them owns it:
#
#     a support gem      register_support_gem("pierce", ..., mod="pierce")
#     a skill tree node  mods=[("pierce", 2)]
#     a gem that always
#     does it            "always": [("pierce", 3)]   in content/gems.py
#     a unique item      the same (name, value) pairs
#
# TAGS decide where a mod is allowed to land. A gem template lists what it
# accepts in "support_tags", and a mod only applies if they overlap. That is
# why a pierce node does nothing to a sword swing, with no extra code in the
# skill tree. A mod with no tags applies to everything.
#
# A new mechanic is ONE function plus ONE register_mod call here. All four
# sources can use it the same day.

mod_types = {}

def register_mod(name, apply, tags=None, describe=None, combine="add"):
    """apply(packets, value) -> packets
    tags      which hits it may change: {"projectile"}, {"melee"}, {"damage"}...
              Matched against a gem's "support_tags". Empty = applies to all.
    describe  describe(value) -> the line shown in tooltips
    combine   how two sources stack IN THE UI: "add" or "mul"
    """
    mod_types[name] = {
        "apply": apply,
        "tags": set(tags) if tags else set(),
        "describe": describe,
        "combine": combine,
    }
    return name

def mod_allowed(name, allowed_tags):
    """True if this mod may touch a hit that accepts `allowed_tags`."""
    mod = mod_types.get(name)
    if mod is None:
        return False
    if not mod["tags"]:
        return True
    return bool(mod["tags"] & set(allowed_tags or ()))

def apply_mod(name, packets, value):
    mod = mod_types.get(name)
    if mod is None:
        print(f"WARNING: mod '{name}' is not registered. See systems/mods.py.")
        return packets
    return mod["apply"](packets, value)

def apply_mods(packets, mods, allowed_tags=None):
    """mods = [(name, value), ...] applied in order.
    allowed_tags=None means "no filtering" (used for a gem's own `always`
    list, which the author chose deliberately)."""
    for name, value in mods or ():
        if allowed_tags is not None and not mod_allowed(name, allowed_tags):
            continue
        packets = apply_mod(name, packets, value)
    return packets

def describe_mod(name, value):
    mod = mod_types.get(name)
    if mod and mod["describe"]:
        return mod["describe"](value)
    return f"{name} {value}"

def mod_tags(name):
    mod = mod_types.get(name)
    return mod["tags"] if mod else set()

def mod_combine(name):
    mod = mod_types.get(name)
    return mod["combine"] if mod else "add"

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
# THE MECHANICS
#
# Each one is the ONLY place that mechanic exists.
# ---------------------------------------------------------------
def scale_key(key):
    """Build a mod that multiplies one field on every packet."""
    def apply(packets, value):
        for p in packets:
            p[key] = p.get(key, 0) * value
        return packets
    return apply

def multiply_key(key):
    """Build a mod that multiplies one field (starting at 1) on every packet.
    Used for damage multipliers: they are applied at the very end, after all flat damage."""
    def apply(packets, value):
        for p in packets:
            p[key] = p.get(key, 1.0) * value
        return packets
    return apply

def add_key(key, to_int=False):
    """Build a mod that adds to one field on every packet."""
    def apply(packets, value):
        for p in packets:
            p[key] = p.get(key, 0) + (int(value) if to_int else value)
        return packets
    return apply

def set_key(key):
    """Build a mod that writes one field on every packet."""
    def apply(packets, value):
        for p in packets:
            p[key] = value
        return packets
    return apply

def add_projectiles(packets, value):
    return spread_packets(packets[0], len(packets) + int(value))

def add_crit_chance(packets, value):
    for p in packets:
        key = "spell_crit_chance_increase" if p.get("crit_type", "attack") == "spell" else "attack_crit_chance_increase"
        p[key] = p.get(key, 0) + value
    return packets

def add_attack_speed(packets, value):
    for p in packets:
        p["cooldown_mult"] = p.get("cooldown_mult", 1.0) / (1 + value / 100)
    return packets

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

def add_effect(name, **defaults):
    """Build a mod that attaches a registered effect (systems/status.py) to
    every hit. The mod's value becomes the field named in `scales`, so one
    mod can be rolled at different strengths.

        register_mod("explode_on_hit",
                     add_effect("explode", radius=150, scales="damage"),
                     tags={"damage"})
    """
    scales = defaults.pop("scales", None)
    def apply(packets, value):
        for p in packets:
            effect = {"name": name, **defaults}
            if scales:
                effect[scales] = value
            p["effects"] = list(p.get("effects", ())) + [effect]
        return packets
    return apply

# --- works on any hit ----------------------------------------------------
register_mod("damage", multiply_key("damage_more"), tags={"damage"}, combine="mul",
             describe=lambda v: f"x{v:.2f} damage")
register_mod("aoe", scale_key("aoe"), tags={"aoe"}, combine="mul",
             describe=lambda v: f"x{v:.2f} area of effect")
register_mod("dot_damage", scale_key("dot_damage"), tags={"dot"}, combine="mul",
             describe=lambda v: f"x{v:.2f} damage over time")
register_mod("crit_damage", add_key("crit_damage"), tags={"crit"},
             describe=lambda v: f"+{int(v)}% critical strike damage")
register_mod("crit_chance", add_crit_chance, tags={"crit"},
             describe=lambda v: f"+{v:.1f}% critical strike chance")
register_mod("attack_speed", add_attack_speed, tags={"attack"},
             describe=lambda v: f"+{int(v)}% attack speed")
register_mod("burst", burst_fire,
             describe=lambda v: f"Fires {int(v)} extra times")
register_mod("explode_on_hit", add_effect("explode", radius=150, scales="damage"),
             tags={"damage"},
             describe=lambda v: f"Hits explode for {int(v)} in a 150 radius")
# --- ailments (systems/ailments.py) - added to the hit, on top of the attacker's own stat ---
register_mod("burn_chance", add_key("burn_chance"), tags={"damage"},
             describe=lambda v: f"+{v:g}% chance to burn")
register_mod("burn_damage", add_key("burn_damage"), tags={"damage"},
             describe=lambda v: f"Burns deal +{v:g}% of the hit's fire damage per second")
register_mod("poison_chance", add_key("poison_chance"), tags={"damage"},
             describe=lambda v: f"+{v:g}% chance to poison")
register_mod("poison_damage", add_key("poison_damage"), tags={"damage"},
             describe=lambda v: f"Poison deals +{v:g}% of max health per stack")
# --- flat added damage: "added_fire", "added_nature_spell", "added_frost_attack"... ---
# These only ADD to the hit. finish_hit_damage() in systems/damage.py adds all flat
# damage together first and multiplies afterwards, so socket order never matters.
from systems.damage import damage_types, flat_conditions
for _type in damage_types:
    register_mod(f"added_{_type}", add_key(f"added_{_type}"), tags={"damage"},
                 describe=lambda v, t=_type: f"Adds {v:g} {t} damage")
    for _cond in flat_conditions:
        register_mod(f"added_{_type}_{_cond}", add_key(f"added_{_type}_{_cond}"), tags={"damage"},
                     describe=lambda v, t=_type, c=_cond: f"Adds {v:g} {t} damage to {c}s")
# --- projectiles only ----------------------------------------------------
register_mod("projectiles", add_projectiles, tags={"projectile"},
             describe=lambda v: f"+{int(v)} projectiles")
register_mod("pierce", add_key("pierce", to_int=True), tags={"projectile"},
             describe=lambda v: f"Pierces {int(v)} more targets")
register_mod("speed", scale_key("speed"), tags={"projectile"}, combine="mul",
             describe=lambda v: f"x{v:.2f} projectile speed")
register_mod("orbit", set_orbit, tags={"projectile"},
             describe=lambda v: f"Orbits you at {int(v)} range")

# --- melee only ----------------------------------------------------------
register_mod("arc", add_key("arc"), tags={"melee"},
             describe=lambda v: f"+{int(v)} degree swing arc")
register_mod("reach", scale_key("range_mult"), tags={"melee"}, combine="mul",
             describe=lambda v: f"x{v:.2f} swing reach")
register_mod("max_targets", add_key("max_targets", to_int=True), tags={"melee"},
             describe=lambda v: f"+{int(v)} targets hit")