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

def register_status(name, apply=None, tick=None, expire=None, blocks=(), describe=None,
                    label=None, color=(255, 255, 255), icon=None):
    """A status that stays on the target for `duration` seconds.

    apply(target, status)       - when applied or refreshed
    tick(target, status, dt)    - every frame while active
    expire(target, status)      - when it runs out
    blocks                      - what the target can't use while it has this
                                  status: {"spell"} (silence), {"attack"}
                                  (disarm), or both (stun). Targets ask
                                  target.is_blocked("spell") instead of
                                  checking for specific status names.
    label                       - text shown above the target, e.g. "Silenced".
                                  Default: the name, e.g. "ember_burn" -> "Ember Burn"
    color                       - colour of the label and timer
    icon                        - sprite name (no .png). If set, the icon is shown
                                  instead of the label. Leave it out = text only.
    """
    if name in status_effect_types or name in hit_effect_types:
        raise ValueError(f"Effect '{name}' is registered twice")
    status_effect_types[name] = {"apply": apply, "tick": tick, "expire": expire, "blocks": set(blocks),
                                 "describe": describe,
                                 "label": label or name.replace("_", " ").title(),
                                 "color": color, "icon": icon}  

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
    title = name.replace("_", " ").title()            # "ember_burst" -> "Ember Burst"
    numbers = ", ".join(f"{k} {v}" for k, v in effect.items() if k != "name")
    return f"{title} ({numbers})" if numbers else title

def status_blocks(statuses, action):
    """True if any active status blocks this action."""
    return any(action in status_effect_types[name]["blocks"] for name in statuses)

class StatusHolder:
    """Parent class for anything that can have statuses (enemies, player, later pets/NPCs).
    Use it like:  class Enemy(StatusHolder):
    The class must set  self.statuses = {}  in its __init__."""

    def apply_status(self, name, duration, **params):
        if name not in status_effect_types:
            return
        status = self.statuses.get(name)
        if status is None:
            status = dict(params)
            status["remaining"] = duration
            self.statuses[name] = status
        else:
            status.update(params)
            status["remaining"] = max(status["remaining"], duration)
        hook = status_effect_types[name]["apply"]
        if hook:
            hook(self, status)

    def update_statuses(self, dt):
        if not self.statuses:
            return
        for name in list(self.statuses):
            status = self.statuses[name]
            config = status_effect_types[name]
            if config["tick"]:
                config["tick"](self, status, dt)
            status["remaining"] -= dt
            if status["remaining"] <= 0:
                del self.statuses[name]
                if config["expire"]:
                    config["expire"](self, status)

    def has_status(self, name):
        return name in self.statuses

    def is_blocked(self, action):
        """True if a status (silence, stun...) stops this action."""
        return status_blocks(self.statuses, action)


def draw_statuses(target, center_x, bottom_y):
    """Draw all active statuses of `target` side by side, centered on center_x,
    with the bottom of the row at bottom_y. Each one is:
            2.4          <- time left
         Silenced        <- label, or the icon if the status has one
    Returns the y of the top of the row, so other things can be drawn above it."""
    if not target.statuses:
        return bottom_y
    from core.state import app
    from core.screen import get_font
    from core.assets import get_ui_scaled

    font = get_font(max(12, int(16 * app.ui_scale)))
    line_height = font.get_height()
    gap = 6                                        # space between two statuses

    # 1. build each status as (timer image, label/icon image, width)
    cells = []
    for name, status in target.statuses.items():
        config = status_effect_types[name]
        timer = font.render(f"{status['remaining']:.1f}", True, config["color"])
        icon = get_ui_scaled(config["icon"], line_height, line_height) if config["icon"] else None
        label = config["label"](status) if callable(config["label"]) else config["label"]
        below = icon or font.render(label, True, config["color"])
        cells.append((timer, below, max(timer.get_width(), below.get_width())))

    # 2. draw them in a row, centered
    total_width = sum(width for _, _, width in cells) + gap * (len(cells) - 1)
    x = center_x - total_width // 2
    top_y = bottom_y - line_height * 2
    for timer, below, width in cells:
        cell_center = x + width // 2
        app.screen.blit(timer, timer.get_rect(midtop=(cell_center, top_y)))
        app.screen.blit(below, below.get_rect(midtop=(cell_center, top_y + line_height)))
        x += width + gap
    return top_y

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

register_status("slow", apply=slow_apply, expire=slow_expire, label="Slowed", color=(120, 180, 255),
                describe=lambda e: f"Slows the target by {e.get('amount', 0) * 100:.0f}% for {e.get('duration', 0):.1f}s")
register_status("dot", tick=dot_tick, label="Damage over time TEST TEST REMOVE", color=(255, 140, 40),
                describe=lambda e: f"Deals {e.get('dps', 0):.0f} damage per second to the target for {e.get('duration', 0):.1f}s")
register_status("silence", blocks={"spell"}, label="Silenced", color=(190, 120, 255),
                describe=lambda e: f"Silences the target for {e.get('duration', 0):.1f}s")

register_hit_effect("explode", explode, describe=lambda e: f"Explodes for {e.get('damage', 0):.0f} damage in a {e.get('radius', 0):.0f} radius")
register_hit_effect("heal_caster", heal_caster, describe=lambda e: (f"Heals you for {e.get('percent')}% of maximum life" if e.get("percent") else f"Heals you for {e.get('amount', 0):.0f}"))