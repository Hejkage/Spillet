# region Status effects and hit effects
#
# Everything that can happen when something is hit goes through here.
# A projectile / melee swing carries a list of effects as plain data:
#
#     effects=[{"name": "slow", "duration": 2.0, "amount": 0.4},
#              {"name": "silence", "duration": 3.0}]
#
# apply_hit_effects() looks up each name and runs it. Two kinds exist:
#
#   STATUS      - lasts a while on the target (slow, burn, silence...).
#                 register_status(name, apply=, tick=, expire=, blocks=)
#   HIT EFFECT  - happens once, right at the hit (explode, spawn something...).
#                 register_hit_effect(name, fn)
#
# New effects can be registered from ANY file, including a content file
# for a single pet. Nothing in projectiles.py / enemies.py needs to change.

status_effect_types = {}
hit_effect_types = {}

def register_status(name, apply=None, tick=None, expire=None, blocks=()):
    """A status that stays on the target for `duration` seconds.

    apply(target, status)       - when applied or refreshed
    tick(target, status, dt)    - every frame while active
    expire(target, status)      - when it runs out
    blocks                      - actions the target can't do while it has
                                  this status, e.g. {"attacking"}. Targets ask
                                  target.is_blocked("attacking") instead of
                                  checking for specific status names.
    """
    if name in status_effect_types or name in hit_effect_types:
        raise ValueError(f"Effect '{name}' is registered twice")
    status_effect_types[name] = {"apply": apply, "tick": tick, "expire": expire, "blocks": set(blocks)}

def register_hit_effect(name, fn):
    """Something that happens once when a hit lands.

    fn(target, effect, source)
        target - what was hit
        effect - the effect dict from the data, e.g. {"name": "explode", "radius": 100}
        source - the projectile / melee swing that hit (may be None)
    """
    if name in status_effect_types or name in hit_effect_types:
        raise ValueError(f"Effect '{name}' is registered twice")
    hit_effect_types[name] = fn

_warned_unknown = set()

def apply_hit_effects(target, effects, source=None):
    """Run every effect in the list on the target."""
    for effect in effects:
        name = effect["name"]
        if name in hit_effect_types:
            hit_effect_types[name](target, effect, source)
        elif name in status_effect_types:
            params = {k: v for k, v in effect.items() if k not in ("name", "duration")}
            target.apply_status(name, effect["duration"], **params)
        elif name not in _warned_unknown:
            _warned_unknown.add(name)
            print(f"Unknown effect '{name}' - did you forget register_status / register_hit_effect?")

def status_blocks(statuses, action):
    """True if any active status blocks this action."""
    return any(action in status_effect_types[name]["blocks"] for name in statuses)

# region Built-in statuses

def slow_apply(enemy, status):
    enemy.slow_multiplier = 1.0 - status.get("amount", 0)

def slow_expire(enemy, status):
    enemy.slow_multiplier = 1.0

def dot_tick(enemy, status, dt):
    enemy.enemy_take_damage(status.get("dps", 0) * dt)

register_status("slow", apply=slow_apply, expire=slow_expire)
register_status("dot", tick=dot_tick)
register_status("silence", blocks={"attacking"})
