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
# ANY effect can have a "chance" (in %). Without one it always happens:
#     {"name": "slow", "chance": 25, "duration": 2.0, "amount": 0.4}
#     {"name": "explode", "chance": 5, "type": "fire", "of": "max_health", "percent": 10, "radius": 150}
#
# New effects can be registered from ANY file, including a content file
# for a single pet. Nothing in projectiles.py / enemies.py needs to change.

status_effect_types = {}
hit_effect_types = {}

def register_status(name, apply=None, tick=None, expire=None, blocks=(), describe=None,
                    label=None, color=(255, 255, 255), icon=None, avoidable=True, avoid_label=None):
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
    avoidable                   - True: it gets a "<name>_immunity" stat, a % chance
                                  to avoid it (100% = immune). False for buffs.
    avoid_label                 - how that stat is written: "Being Slowed" ->
                                  "Chance to Avoid Being Slowed". Default: the name.
    """
    if name in status_effect_types or name in hit_effect_types:
        raise ValueError(f"Effect '{name}' is registered twice")
    status_effect_types[name] = {"apply": apply, "tick": tick, "expire": expire, "blocks": set(blocks),
                                 "describe": describe,
                                 "label": label or name.replace("_", " ").title(),
                                 "color": color, "icon": icon}
    if avoidable:
        from systems.items import register_immunity
        register_immunity(name, avoid_label)

def avoids(target, name):
    """Does the target avoid this status right now? Immune ("immune" set, or 100%
    "<name>_immunity") always does; a lower chance is rolled every time."""
    if name in getattr(target, "immune", ()):
        return True
    chance = getattr(target, f"{name}_immunity", 0)
    import random
    return chance > 0 and random.uniform(0, 100) < chance

def register_hit_effect(name, fn, describe=None, check=None, describe_final=None):
    """Something that happens once when a hit lands.

    fn(target, effect, source)
        target - what was hit
        effect - the effect dict from the data, e.g. {"name": "explode", "radius": 100}
        source - the projectile / melee swing that hit (may be None)
    check(effect) -> [problem, ...]   optional: what's wrong with an effect's data,
                     reported at start-up (a missing "type"...).
    """
    if name in status_effect_types or name in hit_effect_types:
        raise ValueError(f"Effect '{name}' is registered twice")
    hit_effect_types[name] = {"fn": fn, "describe": describe, "check": check, "describe_final": describe_final}

def check_effect(effect):
    """Problems with one effect's data (used by the start-up check)."""
    config = hit_effect_types.get(effect.get("name"))
    problems = []
    if config and config.get("check"):
        problems += config["check"](effect)
    chance = effect.get("chance", 100)
    if not isinstance(chance, (int, float)) or not 0 < chance <= 100:
        problems.append(f"effect '{effect.get('name')}': \"chance\" must be a number from 0 to 100")
    return problems

_warned_unknown = set()

def apply_hit_effects(target, effects, source=None, statuses_only=False):
    """Run every effect in the list on the target. An effect with a "chance"
    only happens that % of the time.
    statuses_only=True: only statuses (slow, silence...) - never hit effects like
    explode / split / chain. For hits that are not the skill (systems/origins.py)."""
    import random
    for effect in effects:
        name = effect["name"]
        if statuses_only and name not in status_effect_types:
            continue
        if "chance" in effect and random.uniform(0, 100) >= effect["chance"]:
            continue
        if name in hit_effect_types:
            hit_effect_types[name]["fn"](target, effect, source)
        elif name in status_effect_types:
            params = {k: v for k, v in effect.items() if k not in ("name", "duration")}
            target.apply_status(name, effect["duration"], **params)
        elif name not in _warned_unknown:
            _warned_unknown.add(name)
            print(f"Unknown effect '{name}' - did you forget register_status / register_hit_effect?")

def describe_effect(effect, final=False):
    """One readable line for a piece of effect data.
    final=False  the effect's OWN numbers - item, gem, tree and support tooltips. Always this.
    final=True   with YOUR stats counted (area, increased damage) - only the stats panel."""
    name = effect["name"]
    config = hit_effect_types.get(name) or status_effect_types.get(name)
    if final and config and config.get("describe_final"):
        text = config["describe_final"](effect)
    elif config and config.get("describe"):
        text = config["describe"](effect)
    else:
        title = name.replace("_", " ").title()            # "ember_burst" -> "Ember Burst"
        numbers = ", ".join(f"{k} {v}" for k, v in effect.items() if k not in ("name", "chance"))
        text = f"{title} ({numbers})" if numbers else title
    return with_chance(text, effect.get("chance", 100))

def with_chance(text, chance):
    """ "Explodes dealing 50 ..." with a 5% chance -> "5% chance to explode dealing 50 ...".
    A describe() text starts with a verb ending in s ("Slows", "Explodes", "Heals"),
    so the chance version just drops that s."""
    if chance >= 100:
        return text
    verb, _, rest = text.partition(" ")
    if verb.endswith("s"):
        return f"{chance:g}% chance to {verb[:-1].lower()} {rest}".rstrip()
    return f"{chance:g}% chance: {text}"

def status_blocks(statuses, action):
    """True if any active status blocks this action."""
    return any(action in status_effect_types[name]["blocks"] for name in statuses)

class StatusHolder:
    """Parent class for anything that can have statuses (enemies, player, later pets/NPCs).
    Use it like:  class Enemy(StatusHolder):
    The class must set  self.statuses = {}  in its __init__."""

    def apply_status(self, name, duration, **params):
        if name not in status_effect_types or avoids(self, name):
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

def haste_apply(target, status):
    target.haste_multiplier = status.get("amount", 1.0)

def haste_expire(target, status):
    target.haste_multiplier = 1.0

def dot_tick(enemy, status, dt):
    from systems.damage import resolve_damage
    from systems.player import player
    source = EffectSource(0, status.get("hit_stats"), 0, attacker=player, origin="dot")   # a kill counts as the gem's
    enemy.enemy_take_damage(resolve_damage(status.get("dps", 0) * dt, status.get("hit_stats"), enemy, player, protectable=False), flash=False, source=source)

def scaled_effect_damage(amount, damage_type, attacker=None):
    """An effect's own damage raised by the attacker's INCREASED damage of that type
    (and its groups, and "increased damage"). Never spell / attack damage, never flat."""
    from systems.damage import increased_only
    if attacker is None:
        from systems.player import player as attacker
    amount = increased_only(amount, damage_type, lambda name, default: getattr(attacker, name, default))
    if hasattr(attacker, "effect_more_damage"):
        amount *= attacker.effect_more_damage()      # your "more damage" too
    return amount

# ---------------------------------------------------------------
# EXPLODE - one explosion, written the same on hit, on kill, on items, trees and supports:
#
#   {"name": "explode",
#    "type": "fire",                 the damage type(s) it deals: "fire" or ["fire", "physical"]
#    "of": "hit",                    what "percent" is taken from:
#                                      "hit"         the hit's damage OF THOSE TYPES only
#                                                    (a fireball's fire part - never its physical part)
#                                      "max_health"  the max health of the enemy it starts from
#    "percent": 30,
#    "damage": 50,                   optional: a flat amount on top
#    "scales": False,                optional: stop YOUR increased / more damage of its type from
#                                    raising the max_health / flat amount (they do by default).
#                                    A "hit" amount is NEVER scaled again - the hit already was.
#    "radius": 150,
#    "chance": 5}                    optional, like every effect
#
# It hits every OTHER enemy in the radius with YOUR stats only - nothing from a gem:
#   - not an attack or spell: no increased spell / attack damage, no flat added damage, no leech
#   - crit: base 0%, so only your ADDED crit chance counts (then increased crit chance)
#   - burn, poison...: your chances, worked out from the explosion's own damage
#   - your penetration and protection penetration
#   - the radius grows with YOUR area of effect (items, passive tree)
#   - never on-hit effects (it can't explode again from hitting), but its kills DO
#     trigger your on-kill effects - up to max_effect_chain explosions in a row.
# ---------------------------------------------------------------
def explode_types(effect):
    types = effect.get("type", effect.get("damage_type"))        # "damage_type": items made before the update
    return [types] if isinstance(types, str) else list(types or ())

def explode_scales(effect):
    """Does your increased / more damage raise the max_health / flat part? Yes, unless "scales": False."""
    return effect.get("scales", True)

# An explosion that kills can trigger another one (on kill), which can kill again...
# This many in a row at most. It only stops a whole map from popping in one frame.
max_effect_chain = 50

class EffectSource:
    """What an explosion hits WITH. On-kill effects it causes get this as their source,
    so they know the damage ("of": "hit") and how many explosions came before."""
    def __init__(self, damage, hit_stats, depth, attacker=None, origin="explosion"):
        self.damage = damage
        self.hit_stats = hit_stats
        self.effect_depth = depth
        self.attacker = attacker
        self.origin = origin

def explosion_parts(target, effect, source):
    """{damage type: amount} this explosion deals, before the targets' defences."""
    from systems.damage import damage_split
    types = explode_types(effect)
    percent = effect.get("percent", 0) / 100
    parts = {t: 0.0 for t in types}
    if effect.get("of") == "hit" and source is not None:
        hit_damage = getattr(source, "damage", 0)
        shares = damage_split(getattr(source, "hit_stats", None))
        for t in types:
            parts[t] += hit_damage * shares.get(t, 0) * percent        # only the hit's damage of this type
    own = {t: effect.get("damage", 0) / len(types) for t in types}     # flat, shared between the types
    if effect.get("of") == "max_health":
        for t in types:
            own[t] += getattr(target, "max_health", 0) * percent / len(types)
    for t in types:
        amount = own[t]
        if explode_scales(effect):
            amount = scaled_effect_damage(amount, t, getattr(source, "attacker", None))
        parts[t] += amount
    return {t: v for t, v in parts.items() if v > 0}

def explode(target, effect, source):
    """Damage every other enemy near the target. Works from a projectile, a melee
    swing, a pet, an on-kill effect - anything that carries effect data."""
    from core.state import world
    from systems.enemies import deal_effect_damage
    depth = getattr(source, "effect_depth", 0) + 1
    if depth > max_effect_chain:
        return
    parts = explosion_parts(target, effect, source)
    if not parts:
        return                                        # a fire explosion from a hit with no fire in it
    from systems.player import player
    hit_stats = {"damage_split": parts}          # only its own damage type(s): no gem stats, not an attack or spell
    from_hit = (getattr(source, "hit_stats", None) or {}).get("on_kill")
    if from_hit:
        hit_stats["on_kill"] = from_hit          # its kills still count as the gem's: its on-kill effects happen
    radius = effect.get("radius", 100) * player.aoe / 100     # YOUR area of effect (items, passive tree) - never a gem's
    total = sum(parts.values())
    blast = EffectSource(total, hit_stats, depth, attacker=player)
    for enemy in list(world.enemies):
        if enemy is not target and enemy.alive:
            if (enemy.x - target.x) ** 2 + (enemy.y - target.y) ** 2 <= radius ** 2:
                deal_effect_damage(enemy, total, hit_stats, attacker=player, label="Explosion", source=blast)

def describe_explode(e, final=False):
    """final=False: its own numbers (tooltips). final=True: with your area and increased
    damage counted (only the stats panel)."""
    types = " and ".join(explode_types(e)) or "?"
    amounts = []
    if e.get("percent"):
        of = "the hit's " + types + " damage" if e.get("of") == "hit" else "the enemy's max health"
        amounts.append(f"{e['percent']:g}% of {of}")
    if e.get("damage"):
        flat = e["damage"]
        if final and explode_scales(e):       # the stats panel: with your increased damage
            flat = sum(scaled_effect_damage(flat / len(explode_types(e)), t) for t in explode_types(e))
        amounts.append(f"{flat:.0f}")
    joint = " as " if e.get("percent") else " "        # "10% of ... as fire damage" / "150 fire damage"
    radius = explosion_radius(e) if final else e.get("radius", 100)
    return f"Explodes dealing {' + '.join(amounts) or '0'}{joint}{types} damage in a {radius:.0f} radius"

def explosion_radius(e):
    """The radius it really has: its own radius with YOUR area of effect."""
    from systems.player import player
    return e.get("radius", 100) * player.aoe / 100

def check_explode(e):
    from systems.damage import damage_types
    problems = []
    types = explode_types(e)
    if not types:
        problems.append('explode needs "type": "fire" (or a list of types)')
    problems += [f"explode: unknown damage type '{t}'" for t in types if t not in damage_types]
    if e.get("percent") and e.get("of") not in ("hit", "max_health"):
        problems.append('explode with "percent" needs "of": "hit" or "max_health"')
    if not e.get("percent") and not e.get("damage"):
        problems.append('explode needs "percent" (with "of") or a flat "damage"')
    return problems

def heal_caster(target, effect, source):
    """Heal the player. `percent` of max health, or a flat `amount`."""
    from systems.player import player
    healed = player.max_health * effect.get("percent", 0) / 100 + effect.get("amount", 0)
    player.heal(healed)

register_status("slow", apply=slow_apply, expire=slow_expire, label="Slowed", color=(120, 180, 255), avoid_label="Being Slowed",
                describe=lambda e: f"Slows the target by {e.get('amount', 0) * 100:.0f}% for {e.get('duration', 0):.1f}s")
register_status("dot", tick=dot_tick, label="Damage over time TEST TEST REMOVE", color=(255, 140, 40), avoidable=False,
                describe=lambda e: f"Deals {e.get('dps', 0):.0f} damage per second to the target for {e.get('duration', 0):.1f}s")
register_status("haste", apply=haste_apply, expire=haste_expire, label="Haste", color=(255, 220, 120), avoidable=False,
                describe=lambda e: f"Moves {e.get('amount', 1):g}x as fast for {e.get('duration', 0):.1f}s")
register_status("silence", blocks={"spell"}, label="Silenced", color=(190, 120, 255), avoid_label="Being Silenced",
                describe=lambda e: f"Silences the target for {e.get('duration', 0):.1f}s")

register_hit_effect("explode", explode, describe=describe_explode, check=check_explode,
                    describe_final=lambda e: describe_explode(e, final=True))
register_hit_effect("heal_caster", heal_caster, describe=lambda e: (f"Heals you for {e.get('percent')}% of maximum life" if e.get("percent") else f"Heals you for {e.get('amount', 0):.0f}"))