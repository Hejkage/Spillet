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

def register_status(name, apply=None, tick=None, expire=None, blocks=(), describe=None):
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
    status_effect_types[name] = {"apply": apply, "tick": tick, "expire": expire, "blocks": set(blocks), "describe": describe}

def register_hit_effect(name, fn, describe=None):
    """Something that happens once when a hit lands.

    fn(target, effect, source)
        target - what was hit
        effect - the effect dict from the data, e.g. {"name": "explode", "radius": 100}
        source - the projectile / melee swing that hit (may be None)
    """
    if name in status_effect_types or name in hit_effect_types:
        raise ValueError(f"Effect '{name}' is registered twice")
    hit_effect_types[name] = {"fn": fn, "describe": describe}

_warned_unknown = set()

def apply_hit_effects(target, effects, source=None):
    """Run every effect in the list on the target."""
    for effect in effects:
        name = effect["name"]
        if name in hit_effect_types:
            hit_effect_types[name]["fn"](target, effect, source)
        elif name in status_effect_types:
            params = {k: v for k, v in effect.items() if k not in ("name", "duration")}
            target.apply_status(name, effect["duration"], **params)
        elif name not in _warned_unknown:
            _warned_unknown.add(name)
            print(f"Unknown effect '{name}' - did you forget register_status / register_hit_effect?")

def describe_effect(effect):
    """One readable line for a piece of effect data. Used by tooltips.
    The effect's own describe() wins; otherwise its numbers are listed."""
    name = effect["name"]
    config = hit_effect_types.get(name) or status_effect_types.get(name)
    if config and config.get("describe"):
        return config["describe"](effect)
    numbers = ", ".join(f"{k} {v}" for k, v in effect.items() if k != "name")
    return f"{name} ({numbers})" if numbers else name

def status_blocks(statuses, action):
    """True if any active status blocks this action."""
    return any(action in status_effect_types[name]["blocks"] for name in statuses)

# region Built-in statuses

def slow_apply(enemy, status):
    enemy.slow_multiplier = 1.0 - status.get("amount", 0)

def slow_expire(enemy, status):
    enemy.slow_multiplier = 1.0

def dot_tick(enemy, status, dt):
    from systems.damage import resolve_damage
    from systems.player import player
    enemy.enemy_take_damage(resolve_damage(status.get("dps", 0) * dt, status.get("hit_stats"), enemy, player, protectable=False))

def explode(target, effect, source):
    """Damage everything near the target. Works from a projectile, a melee
    swing, a pet, an on-kill effect - anything that carries effect data."""
    from core.state import world
    from systems.damage import resolve_damage
    from systems.player import player
    radius = effect.get("radius", 100)
    damage = effect.get("damage", 0)
    hit_stats = getattr(source, "hit_stats", None)
    for enemy in world.enemies:
        if enemy is not target and enemy.alive:
            if (enemy.x - target.x) ** 2 + (enemy.y - target.y) ** 2 <= radius ** 2:
                enemy.enemy_take_damage(resolve_damage(damage, hit_stats, enemy, player))

def heal_caster(target, effect, source):
    """Heal the player. `percent` of max health, or a flat `amount`."""
    from systems.player import player
    healed = player.max_health * effect.get("percent", 0) / 100 + effect.get("amount", 0)
    player.heal(healed)

register_status("slow", apply=slow_apply, expire=slow_expire, describe=lambda e: f"Slows by {e.get('amount', 0) * 100:.0f}% for {e.get('duration', 0):.1f}s")
register_status("dot", tick=dot_tick, describe=lambda e: f"{e.get('dps', 0):.0f} damage per second for {e.get('duration', 0):.1f}s")
register_status("silence", blocks={"attacking"}, describe=lambda e: f"Silenced for {e.get('duration', 0):.1f}s")

register_hit_effect("explode", explode, describe=lambda e: f"Explodes for {e.get('damage', 0):.0f} damage in a {e.get('radius', 0):.0f} radius")
register_hit_effect("heal_caster", heal_caster, describe=lambda e: (f"Heals you for {e.get('percent')}% of maximum life" if e.get("percent") else f"Heals you for {e.get('amount', 0):.0f}"))