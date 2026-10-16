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
# NEEDS decide where a mod is allowed to land (tags: systems/tags.py). A mod
# lands on an ability only if the ability has EVERY tag the mod needs. That is
# why a pierce node does nothing to a sword swing, with no extra code in the
# skill tree. A mod that needs nothing applies to everything.
# SCALES is the damage a mod adds ("added_fire" scales {"fire"}): an ability
# that has it in "blocked" refuses the mod.
#
# A new mechanic is ONE function plus ONE register_mod call here. All four
# sources can use it the same day.

mod_types = {}

def register_mod(name, apply, needs=None, scales=None, describe=None, combine="add"):
    """apply(packets, value) -> packets
    needs     tags the ability must ALL have: {"projectile"}, {"melee"}, {"damage", "spell"}...
              Empty = applies to everything.
    scales    damage types it adds, e.g. {"fire"}. An ability that blocks them refuses it.
    describe  describe(value) -> the line shown in tooltips
    combine   how two sources stack IN THE UI: "add" or "mul"
    """
    mod_types[name] = {
        "apply": apply,
        "needs": set(needs or ()),
        "scales": set(scales or ()),
        "describe": describe,
        "combine": combine,
    }
    return name

def mod_allowed(name, ability_tags, blocked=()):
    """True if this mod may land on an ability with these tags / blocked set."""
    from systems.tags import fits
    mod = mod_types.get(name)
    if mod is None:
        return False
    return fits(mod["needs"], mod["scales"], ability_tags, blocked)

def apply_mod(name, packets, value):
    mod = mod_types.get(name)
    if mod is None:
        print(f"WARNING: mod '{name}' is not registered. See systems/mods.py.")
        return packets
    return mod["apply"](packets, value)

def apply_mods(packets, mods, ability_tags=None, blocked=()):
    """mods = [(name, value), ...] applied in order.
    ability_tags=None means "no filtering" (used for a gem's own `always`
    list, which the author chose deliberately)."""
    for name, value in mods or ():
        if ability_tags is not None and not mod_allowed(name, ability_tags, blocked):
            continue
        packets = apply_mod(name, packets, value)
    return packets

def describe_mod(name, value):
    mod = mod_types.get(name)
    if mod and mod["describe"]:
        return mod["describe"](value)
    return f"{name} {value}"

def mod_needs(name):
    mod = mod_types.get(name)
    return mod["needs"] if mod else set()

def mod_scales(name):
    mod = mod_types.get(name)
    return mod["scales"] if mod else set()

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
        key = "spell_crit_chance_increase" if p.get("hit_type", "attack") == "spell" else "attack_crit_chance_increase"
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
                     needs={"damage"})
    """
    scales = defaults.pop("scales", None)
    stack = defaults.pop("stack", False)
    def apply(packets, value):
        for p in packets:
            effects = list(p.get("effects", ()))
            same = [i for i, e in enumerate(effects) if e["name"] == name] if (stack and scales) else []
            if same:
                # stack=True: add to the one already there (split 5 + split 3 = ONE split of 8)
                old = effects[same[0]]
                effects[same[0]] = {**old, scales: old.get(scales, 0) + value}
            else:
                effect = {"name": name, **defaults}
                if scales:
                    effect[scales] = value
                effects.append(effect)
            p["effects"] = effects
        return packets
    return apply

def add_flat_crit_chance(packets, value):
    """FLAT crit chance (+5 = 5% more chance on top of the base), for this hit's spell/attack."""
    for p in packets:
        key = "spell_crit_chance" if p.get("hit_type", "attack") == "spell" else "attack_crit_chance"
        p[key] = p.get(key, 0) + value
    return packets

def more_text(value, label):
    """1.12 -> "12% more damage", 0.9 -> "10% less damage"."""
    percent = round((value - 1) * 100, 1)
    return f"{percent:g}% more {label}" if percent >= 0 else f"{-percent:g}% less {label}"

# HOW TO TELL THEM APART - the NAME of a mod says what kind of bonus it is:
#   added_...      FLAT: adds a number.            ("added_fire", 10)        +10 fire damage
#                                                  ("added_crit_chance", 5)  +5% crit chance
#   increased_...  INCREASED: a percent. All increased bonuses are ADDED together
#                  first, then applied once.       ("increased_damage", 2)   2% increased damage
#   damage, aoe, speed, reach, dot_damage
#                  MORE: a multiplier. Each one multiplies separately, so they
#                  are stronger together.           ("damage", 1.12)          12% more damage
#   crit_chance    INCREASED crit chance            ("crit_chance", 80)       80% increased crit chance

# --- works on any hit ----------------------------------------------------
register_mod("damage", multiply_key("damage_more"), needs={"damage"}, combine="mul",
             describe=lambda v: more_text(v, "damage"))
register_mod("aoe", scale_key("aoe"), needs={"aoe"}, combine="mul",
             describe=lambda v: more_text(v, "area of effect"))
register_mod("dot_damage", scale_key("dot_damage"), needs={"dot"}, combine="mul",
             describe=lambda v: more_text(v, "damage over time"))
register_mod("crit_damage", add_key("crit_damage"), needs={"damage"},
             describe=lambda v: f"+{int(v)}% critical strike damage")
register_mod("crit_chance", add_crit_chance, needs={"damage"},
             describe=lambda v: f"{v:g}% increased critical strike chance")
register_mod("added_crit_chance", add_flat_crit_chance, needs={"damage"},
             describe=lambda v: f"+{v:g}% critical strike chance")
register_mod("attack_speed", add_attack_speed, needs={"attack"},
             describe=lambda v: f"+{int(v)}% attack speed")
register_mod("cooldown_reduction", add_key("cooldown_reduction"), needs={"spell"},
             describe=lambda v: f"{v:g}% cooldown reduction")
register_mod("burst", burst_fire, needs={"projectile"},
             describe=lambda v: f"Fires {int(v)} extra times")
register_mod("explode_on_hit", add_effect("explode", radius=150, scales="damage"),
             needs={"damage"},
             describe=lambda v: f"Hits explode for {int(v)} in a 150 radius")
# --- ailments (systems/ailments.py) - added to the hit, on top of the attacker's own stat ---
register_mod("burn_chance", add_key("burn_chance"), needs={"damage"},
             describe=lambda v: f"+{v:g}% chance to burn")
register_mod("burn_damage", add_key("burn_damage"), needs={"damage"},
             describe=lambda v: f"Burns deal +{v:g}% of the hit's fire damage per second")
register_mod("poison_chance", add_key("poison_chance"), needs={"damage"},
             describe=lambda v: f"+{v:g}% chance to poison")
register_mod("poison_damage", add_key("poison_damage"), needs={"damage"},
             describe=lambda v: f"Poison deals +{v:g}% of max health per stack")
# --- flat added damage: "added_fire", "added_nature_spell", "added_frost_attack"... ---
# These only ADD to the hit. finish_hit_damage() in systems/damage.py adds all flat
# damage together first and multiplies afterwards, so socket order never matters.
from systems.damage import damage_types, flat_conditions
for _type in damage_types:
    register_mod(f"added_{_type}", add_key(f"added_{_type}"), needs={"damage"}, scales={_type},
                 describe=lambda v, t=_type: f"Adds {v:g} {t} damage")
    for _cond in flat_conditions:
        register_mod(f"added_{_type}_{_cond}", add_key(f"added_{_type}_{_cond}"), needs={"damage", _cond}, scales={_type},
                     describe=lambda v, t=_type, c=_cond: f"Adds {v:g} {t} damage to {c}s")
# --- increased damage on THIS hit only: "increased_damage", "increased_fire", "increased_spell"... ---
# Added to the player's own increased stats for the same key (finish_hit_damage in systems/damage.py).
from systems.damage import damage_keys
for _key in ["damage", *damage_keys]:
    register_mod(f"increased_{_key}", add_key(f"increased_{_key}"), needs={"damage"},
                 describe=lambda v, k=_key: f"{v:g}% increased {'' if k == 'damage' else k + ' '}damage")
# --- increased for things that aren't damage --------------------------------
# "increased_projectile_speed", 5  ->  added to the player's own Projectile Speed stat.
# A new one = one line in this list (the player's stat, the key on the hit) + a register_mod.
increased_hit_stats = [("projectile_speed", "speed"), ("aoe", "aoe")]

def finish_increased_stats(packets, stat):
    """Run once at the end of build_hit_packets(): the player's stat + the
    increased_ mods on this hit are ADDED, then applied once."""
    for p in packets:
        for player_stat, key in increased_hit_stats:
            extra = p.get(f"increased_{player_stat}", 0)
            if extra:
                have = stat(player_stat, 100) or 100
                p[key] = p[key] * (have + extra) / have

register_mod("increased_aoe", add_key("increased_aoe"), needs={"aoe"},
             describe=lambda v: f"{v:g}% increased area of effect")
# --- projectiles only ----------------------------------------------------
register_mod("increased_projectile_speed", add_key("increased_projectile_speed"), needs={"projectile"},
             describe=lambda v: f"{v:g}% increased projectile speed")
register_mod("projectiles", add_projectiles, needs={"projectile"},
             describe=lambda v: f"+{int(v)} projectiles")
register_mod("pierce", add_key("pierce", to_int=True), needs={"projectile"},
             describe=lambda v: f"Pierces {int(v)} more targets")
register_mod("speed", scale_key("speed"), needs={"projectile"}, combine="mul",
             describe=lambda v: more_text(v, "projectile speed"))
register_mod("orbit", set_orbit, needs={"projectile"},
             describe=lambda v: f"Orbits you at {int(v)} range")
register_mod("split", add_effect("split", damage_mult=0.25, size_mult=0.6, scales="count", stack=True),
             needs={"projectile"},
             describe=lambda v: f"On hit, fires {int(v)} smaller projectiles in a circle (25% damage)")
register_mod("chain", add_effect("chain", damage_mult=0.8, range=400, scales="count", stack=True),
             needs={"projectile"},
             describe=lambda v: f"Chains to {int(v)} more enemies (-20% damage per chain)")

# --- melee only ----------------------------------------------------------
register_mod("arc", add_key("arc"), needs={"melee"},
             describe=lambda v: f"+{int(v)} degree swing arc")
register_mod("reach", scale_key("range_mult"), needs={"melee"}, combine="mul",
             describe=lambda v: more_text(v, "swing reach"))
register_mod("max_targets", add_key("max_targets", to_int=True), needs={"melee"},
             describe=lambda v: f"+{int(v)} targets hit")