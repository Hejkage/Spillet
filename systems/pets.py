import pygame
import random, math
from core.state import app, world
from core.assets import scaled_sprites
from core.sounds import play_sound
from systems.projectiles import Projectile
from systems.rarity import (rarity_common, rarity_uncommon, rarity_rare, rarity_epic, rarity_legendary)
from systems.items import register_stat, stat_defs, stat_label, stat_is_percent, tooltip_section, panel_rows

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Pets/Minions

pet_teleport_distance = 1100

# ---------------------------------------------------------------
# PET STATS
#
# A pet has its own stats, like the player. Pets never have life and are
# never hit, so there is no health/defence here.
#
#   register_pet_stat("buff_effect", "Buff Effect", default=100, percent=True)
#
# Every pet stat also creates a PLAYER stat called "pet_<key>"
# ("pet_buff_effect"). Put that on items / the skill tree and it is handed to
# every pet: "20% increased pet buff effect" -> each pet gets 20% increased
# buff effect. Nothing else needs to change.
#
# Where a pet's final value comes from (same maths as the player):
#   (base + flat) * (1 + increased)
#   base      = the pet's own number (register_pet stats), scaled by rarity
#   flat /
#   increased = the player's "pet_<key>" stats + the pet's own tree + auras
#               from other pets
# ---------------------------------------------------------------
pet_stat_defs = {}

def register_pet_stat(key, label, default=0, percent=False, rarity_scaled=False,
                      player_stat=True, player_base=100, show=True):
    """
    default        value a pet has if its register_pet() doesn't set one
    rarity_scaled  multiply the pet's base value by its rarity multiplier
    player_stat    also make a "pet_<key>" stat for the player (items/tree)
    player_base    100 = the player stat is shown as "x% increased", 0 = a flat number
    show           show it in the pet's tooltip
    """
    pet_stat_defs[key] = {"label": label, "default": default, "percent": percent,
                          "rarity_scaled": rarity_scaled, "show": show}
    if player_stat:
        register_stat("pet_" + key, "Pet " + label, base=player_base, tab="pets",
                      percent=percent and player_base == 0,
                      panel_label=("Increased Pet " + label) if player_base == 100 else None)
    return key

register_pet_stat("damage",         "Damage",            default=100, percent=True)
register_pet_stat("attack_speed",   "Attack Speed",      default=100, percent=True)     # attacks only
register_pet_stat("cooldown",       "Cooldown Reduction", default=0,  percent=True, player_base=0)   # spells only
register_pet_stat("movement_speed", "Movement Speed",    default=300)
register_pet_stat("buff_effect",    "Buff Effect",       default=100, percent=True)
register_pet_stat("crit_chance",    "Crit Chance",       default=5,   percent=True, rarity_scaled=True, player_base=0)
register_pet_stat("crit_damage",    "Crit Damage",       default=150, percent=True, player_base=0)
register_pet_stat("ability_damage", "Ability Damage",    default=0,   rarity_scaled=True, player_stat=False, show=False)

# Increased damage per type and group: "fire_damage", "elemental_damage", "spell_damage"...
# Pets start at 100 (= no bonus), and the player gets "pet_fire_damage" etc. for gear.
from systems.damage import damage_keys
for _key in damage_keys:
    register_pet_stat(f"{_key}_damage", f"{_key.replace('_', ' ').title()} Damage",
                      default=100, percent=True, show=False)

# How much better each rarity is. Applies to every stat with rarity_scaled=True
# AND to the amount of every buff. A pet can override single values per rarity
# with rarity_overrides= in register_pet().
pet_rarity_multipliers = {
    rarity_common:    1.0,
    rarity_uncommon:  1.15,
    rarity_rare:      1.3,
    rarity_epic:      1.45,
    rarity_legendary: 1.6,
}

def pet_base_stats(pet_type, rarity):
    """The pet's own numbers at this rarity, before the player, tree or auras.
    Returns (values, buffs)."""
    config = pet_configs[pet_type]
    mult = pet_rarity_multipliers.get(rarity, 1.0)

    values = {k: d["default"] for k, d in pet_stat_defs.items()}
    values.update(config["stats"])
    for key, d in pet_stat_defs.items():
        if d["rarity_scaled"] and isinstance(values.get(key), (int, float)):
            values[key] = values[key] * mult
    buffs = [dict(b, amount=b["amount"] * mult) for b in config["buffs"]]

    for key, value in config["rarity_overrides"].get(rarity, {}).items():
        if key == "buffs":
            buffs = [dict(b) for b in value]
        else:
            values[key] = value
    return values, buffs

def player_pet_mods(player):
    """The player's "pet_<key>" stats, as mods for a pet: [{"stat", "type", "amount"}]."""
    mods = []
    if player is None:
        return mods
    for player_key in stat_defs:
        if not player_key.startswith("pet_"):
            continue
        pet_key = player_key[len("pet_"):]
        flat = player.added_flat.get(player_key, 0)
        increased = player.increased.get(player_key, 0)
        if flat:
            mods.append({"stat": pet_key, "type": "flat", "amount": flat})
        if increased:
            mods.append({"stat": pet_key, "type": "increased", "amount": increased * 100})
    return mods

def apply_pet_mods(base, mods):
    """(base + flat) * (1 + increased) for every stat a mod touches.
    Mods use the same shape as item stats: {"stat": ..., "type": "flat"/"increased", "amount": ...}."""
    flat, increased = {}, {}
    for mod in mods:
        stat = mod.get("stat")
        if mod.get("type") == "flat":
            flat[stat] = flat.get(stat, 0) + mod.get("amount", 0)
        elif mod.get("type") == "increased":
            increased[stat] = increased.get(stat, 0) + mod.get("amount", 0) / 100
    values = dict(base)
    for stat in set(flat) | set(increased):
        start = base.get(stat, 0)
        if not isinstance(start, (int, float)):
            continue
        values[stat] = (start + flat.get(stat, 0)) * (1 + increased.get(stat, 0))
    return values

def scaled_buffs(buffs, values):
    """The pet's buffs after its buff effect: 20 fire at 120% buff effect = 24 fire."""
    effect = values.get("buff_effect", 100) / 100
    return [dict(b, amount=b["amount"] * effect) for b in buffs]

def pet_hit(values):
    """What ONE hit from this pet deals before the target: (damage, hit_stats).
    Uses the same final_damage() as gems, so added flat damage, increased
    damage of a type, spell/attack etc. all work for pets with their own stats."""
    from systems.damage import final_damage
    damage_type = values.get("damage_type", "physical")
    hit_type = values.get("hit_type", "attack")           # "attack" or "spell"
    hit_stats = {"damage_type": damage_type, "crit_type": hit_type}
    if values.get("damage_split"):
        hit_stats["damage_split"] = dict(values["damage_split"])      # e.g. {"nature": 60, "fire": 40}
    if values.get("cannot_scale"):
        hit_stats["cannot_scale"] = set(values["cannot_scale"])        # e.g. {"elemental"}
    total, parts = final_damage(values.get("ability_damage", 0), hit_stats,
                                lambda name, default: values.get(name, default))
    mult = values.get("damage", 100) / 100
    parts = {t: v * mult for t, v in parts.items()}
    hit_stats["damage_split"] = parts
    return total * mult, hit_stats

def pet_ability_cooldown(values):
    """Same rule as gems (systems/abilities.py, template_speed_stat):
    an ATTACK gets faster with attack speed, a SPELL with cooldown reduction.
    Never both."""
    base = values.get("ability_cooldown", 3.0)
    if values.get("hit_type", "attack") == "attack":
        return base / max(0.01, values.get("attack_speed", 100) / 100)
    return base * max(0.1, 1 - values.get("cooldown", 0) / 100)

# ---------------------------------------------------------------
# PET ABILITIES
# ---------------------------------------------------------------
def nearest_enemy(x, y, max_range):
    best = None
    best_dist = max_range
    for e in world.enemies:
        if not e.alive:
            continue
        dx = e.x - x
        dy = e.y - y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= best_dist:
            best = e
            best_dist = dist
    return best

def make_pet_projectile_ability(sprite_name, effects=None, name="Projectile"):
    def ability(pet, player, dt):
        pet.ability_timer -= dt
        if pet.ability_timer > 0:
            return

        target = nearest_enemy(pet.x, pet.y, pet.get_stat("ability_range", 500))
        if target is None:
            pet.ability_timer = 0
            return

        damage, hit_stats = pet_hit(pet.values)
        direction = pygame.Vector2(target.x - pet.x, target.y - pet.y)
        world.projectiles.append(Projectile(
            sprite_name, pet.x, pet.y, direction,
            speed=pet.get_stat("ability_projectile_speed", 600),
            damage=damage,
            aoe=1.0,
            hit_stats=hit_stats,
            effects=effects,
            attacker=pet,             # crits/penetration use the PET's stats
        ))
        pet.ability_timer = pet.ability_cooldown()
    ability.ability_name = name                # shown in tooltips
    ability.effects = list(effects or [])      # so the tooltip can describe what a hit does
    return ability

def make_pet_heal_ability(name="Heal"):
    """Heals the PLAYER for "heal_amount" every "ability_cooldown" seconds.
    Needs no enemy, so it also works out of combat.
    Set "heal_amount" in the pet's stats, or per rarity in rarity_overrides."""
    def ability(pet, player, dt):
        pet.ability_timer -= dt
        if pet.ability_timer > 0:
            return
        amount = pet.get_stat("heal_amount", 0)
        if player.current_health < player.max_health:
            player.heal(amount)
            from systems.popups import spawn_floating_text
            spawn_floating_text(f"+{amount:.0f}", player.x, player.y - 40, color=(120, 255, 120))
        pet.ability_timer = pet.ability_cooldown()
    ability.ability_name = name
    ability.effects = []
    # Own tooltip, because a heal has no damage / crit lines (see pet_tooltip_lines)
    ability.tooltip = lambda values: [
        (f"Heals you for {values.get('heal_amount', 0):.0f} every {pet_ability_cooldown(values):.1f}s", _EFFECT),
    ]
    return ability
# ---------------------------------------------------------------
# MOVEMENT - how a pet travels towards its spot next to the player.
# A pet picks one with "movement": "walk" in its stats.
#
# register_pet_movement(name, move, setup=None)
#   move(pet, dt, target_x, target_y, dx, dy, distance)
#       called every frame while the pet is too far from its spot
#   setup(pet)
#       optional, runs once when the pet is created (for timers etc.)
#
# A movement reads its settings with pet.get_stat("name", default), so new
# settings never need changes to the Pet class.
# pet.speed_multiplier() is 1.0 normally, 1.2 with 20% increased movement speed.
# ---------------------------------------------------------------
pet_movements = {}

def register_pet_movement(name, move, setup=None, tick=None):
    """tick(pet, dt) - optional, runs EVERY frame, also while the pet stands still.
    Count cooldowns down here, so they never freeze while the pet is idle."""
    if name in pet_movements:
        raise ValueError(f"Pet movement '{name}' is registered twice")
    pet_movements[name] = {"move": move, "setup": setup, "tick": tick}

def walk_move(pet, dt, target_x, target_y, dx, dy, distance):
    move_dir = pygame.Vector2(dx, dy).normalize()
    speed = pet.get_stat("movement_speed", 300)
    pet.x += move_dir.x * speed * dt
    pet.y += move_dir.y * speed * dt

def leap_setup(pet):
    pet.leap_timer = 0.0

def leap_tick(pet, dt):
    pet.leap_timer -= dt

def leap_move(pet, dt, target_x, target_y, dx, dy, distance):
    from systems.player import begin_leap
    faster = pet.speed_multiplier()
    if pet.leap_timer <= 0:
        begin_leap(pet, target_x, target_y,
                   pet.get_stat("leap_height", 100),
                   pet.get_stat("leap_time_per_unit", 0.002) / faster,
                   pet.get_stat("leap_max_distance", 700),
                   min_distance=pet.get_stat("leap_min_distance", 0),
                   scatter=pet.get_stat("leap_scatter", 0))
        pet.leap_timer = pet.get_stat("leap_cooldown", 0.0) / faster

register_pet_movement("walk", walk_move)
register_pet_movement("leap", leap_move, setup=leap_setup, tick=leap_tick)


class Pet:
    def __init__(self, pet_type, x, y, rarity=rarity_common, source_item=None):
        config = pet_configs[pet_type]

        self.pet_type = pet_type
        self.rarity = rarity
        self.source_item = source_item
        self.sprite_name = config["sprite"]
        self.base_values, self.base_buffs = pet_base_stats(pet_type, rarity)
        self.values = dict(self.base_values)      # final stats, filled by recalculate_stats()
        self.buffs = []                           # final buffs, after buff effect
        self.damage_totals = {}
        self.x = x
        self.y = y
        self.follow_distance = 80                                  # starts moving when this far from its spot
        self.arrive_distance = self.get_stat("arrive_distance", 10)  # ...and keeps going until this close
        self.returning = False
        self.ability_timer = 0
        self.sound_name = self.get_stat("sound")
        self.sound_interval = self.get_stat("sound_interval", 5.0)
        self.sound_volume = self.get_stat("sound_volume", 1.0)
        self.sound_timer = random.uniform(0, self.sound_interval)
        self.leap = None                       # used by the shared leap code in player.py
        self.movement = self.get_stat("movement", "walk")
        if self.movement not in pet_movements:
            raise KeyError(f"Pet '{pet_type}' uses unknown movement '{self.movement}'. "
                           f"Known: {sorted(pet_movements)}")
        setup = pet_movements[self.movement]["setup"]
        if setup:
            setup(self)

        sprite = scaled_sprites[self.sprite_name]
        self.rect = sprite.get_rect()
        self.summon_key = None
        base_angle = random.uniform(0, 360)
        radius = random.uniform(45, 90)
        self.follow_offset = pygame.Vector2(radius, 0).rotate(base_angle)
        self.follow_jitter_seed = random.uniform(0, 1000)

    def get_stat(self, stat_name, default=None):
        """The pet's FINAL value of a stat (rarity, player, tree and auras included)."""
        return self.values.get(stat_name, default)

    def tree_mods(self):
        """Stat mods from the nodes allocated in this pet's tree."""
        if self.source_item is None:
            return []
        from systems.gemtree import tree_stats
        return tree_stats(self.source_item)

    def recalculate_stats(self, player, incoming_buffs=()):
        """Called by update_pet_stats(). Never call it every frame yourself."""
        from systems.damage import fold_damage_stats
        mods = player_pet_mods(player) + self.tree_mods() + list(incoming_buffs)
        self.values = apply_pet_mods(self.base_values, mods)
        self.buffs = scaled_buffs(self.base_buffs, self.values)
        self.damage_totals = fold_damage_stats(lambda s: self.values.get(s, 0))

    def speed_multiplier(self):
        base = self.base_values.get("movement_speed") or 1
        return max(0.01, self.get_stat("movement_speed", base) / base)

    def ability_cooldown(self):
        return pet_ability_cooldown(self.values)

    def crit_stats(self, hit_stats=None):
        """Same shape as player.crit_stats(), so the damage code can use either."""
        s = hit_stats or {}
        chance = self.get_stat("crit_chance", 0) + s.get("crit_chance", 0)
        return chance, self.get_stat("crit_damage", 150) + s.get("crit_damage", 0)

    def pet_update(self, player, dt):
        from systems.player import update_leap
        if self.sound_name:
            self.sound_timer -= dt
            if self.sound_timer <= 0:
                play_sound(self.sound_name, self.sound_volume)
                self.sound_timer = self.sound_interval

        dx = player.x - self.x
        dy = player.y - self.y
        if (dx * dx + dy * dy) ** 0.5 > pet_teleport_distance:
            self.x = player.x + self.follow_offset.x
            self.y = player.y + self.follow_offset.y

        tick = pet_movements[self.movement]["tick"]
        if tick:
            tick(self, dt)

        if update_leap(self, dt):
            return

        self.follow_jitter_seed += dt
        wobble = pygame.Vector2(
            math.sin(self.follow_jitter_seed * 0.8) * 12,
            math.cos(self.follow_jitter_seed * 0.6) * 12,
        )
        target_x = player.x + self.follow_offset.x + wobble.x
        target_y = player.y + self.follow_offset.y + wobble.y

        dx = target_x - self.x
        dy = target_y - self.y
        distance = (dx * dx + dy * dy) ** 0.5

        if distance > self.follow_distance:
            self.returning = True
        elif distance <= self.arrive_distance:
            self.returning = False
        if self.returning:
            pet_movements[self.movement]["move"](self, dt, target_x, target_y, dx, dy, distance)

        ability = self.get_stat("ability")
        if ability:
            ability(self, player, dt)

    def get_sort_y(self):
        return self.y

    def draw_pet(self, camera):
        from systems.player import leap_height_offset
        sprite = scaled_sprites[self.sprite_name]
        pos = camera.apply_camera(self.x, self.y)
        offset = leap_height_offset(self)
        self.rect = sprite.get_rect(center=(pos[0], pos[1] - int(offset)))
        app.screen.blit(sprite, self.rect)

# ---------------------------------------------------------------
# AURAS / BUFFS
#
# A buff is an item-style stat line plus who it reaches:
#   {"stat": "added_fire_spell", "type": "flat", "amount": 20, "targets": ["player", "pets"]}
#
# targets: "player", "pets" (every pet, itself included), "other_pets", "self"
# Several pets with the same buff all stack.
# ---------------------------------------------------------------
default_buff_targets = ("player", "pets")

def buff_reaches(buff, source, pet):
    targets = buff.get("targets", default_buff_targets)
    if "pets" in targets:
        return True
    if "other_pets" in targets and pet is not source:
        return True
    return "self" in targets and pet is source

def update_pet_stats(player):
    """Called from player.recalculate_stats(). Returns the buffs for the player.

    1. every pet works out its stats from the player + its own tree
       (this is where its buff effect comes from)
    2. every pet's buffs are collected
    3. every pet works out its stats again, now with the other pets' buffs
    """
    pets = player.pets
    for pet in pets:
        pet.recalculate_stats(player)

    all_buffs = [(pet, buff) for pet in pets for buff in pet.buffs]

    for pet in pets:
        incoming = [buff for source, buff in all_buffs if buff_reaches(buff, source, pet)]
        pet.recalculate_stats(player, incoming)

    return [buff for source, buff in all_buffs if "player" in buff.get("targets", default_buff_targets)]

def pet_signature(pets):
    """Changes when anything that changes pet stats changes (used to skip work)."""
    return tuple((id(p), p.rarity, frozenset(getattr(p.source_item, "allocated", ()))) for p in pets)

# ---------------------------------------------------------------
# TEXT - tooltips, the stats panel and tree nodes all use this.
# ---------------------------------------------------------------
def _number(value):
    rounded = round(value, 1)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"

def describe_pet_mod(mod):
    """One stat line: "+24 Added Fire Damage to Spells", "+100% increased Buff Effect"."""
    stat = mod.get("stat")
    if stat in pet_stat_defs:
        label, percent = pet_stat_defs[stat]["label"], pet_stat_defs[stat]["percent"]
    else:
        label, percent = stat_label(stat), stat_is_percent(stat)
    amount = mod.get("amount", 0)
    if mod.get("type") == "increased":
        return f"+{_number(amount)}% increased {label}"
    return f"+{_number(amount)}{'%' if percent else ''} {label}"

# Who an aura reaches, as the start of a sentence. Add a line for a new combination.
_aura_targets_text = {
    frozenset({"player", "pets"}):       "All allies gain",
    frozenset({"player"}):               "You gain",
    frozenset({"pets"}):                 "Your pets gain",
    frozenset({"other_pets"}):           "Your other pets gain",
    frozenset({"self"}):                 "This pet gains",
    frozenset({"player", "other_pets"}): "You and your other pets gain",
}

def describe_buff(buff):
    """"All allies gain +26 Added Fire Damage to Spells" """
    targets = frozenset(buff.get("targets", default_buff_targets))
    who = _aura_targets_text.get(targets, " and ".join(sorted(targets)) + " gain")
    return f"{who} {describe_pet_mod(buff)}"

_WHITE = (255, 255, 255)
_TITLE = (255, 220, 120)
_BUFF = (140, 200, 255)
_EFFECT = (200, 170, 255)

def pet_tooltip_lines(values, buffs):
    """What a pet does: its ability, then its auras. Used by the pet ITEM
    (base numbers) and the pet in the hotbar row (real numbers), so the two
    always look the same."""
    from systems.damage import damage_lines
    from systems.status import describe_effect
    lines = []

    ability = values.get("ability")
    if ability and hasattr(ability, "tooltip"):          # abilities that don't deal damage (heals, buffs...)
        lines.append((getattr(ability, "ability_name", "Ability"), _TITLE))
        lines.extend(ability.tooltip(values))
    elif ability:
        lines.append((getattr(ability, "ability_name", "Ability"), _TITLE))
        damage, hit_stats = pet_hit(values)
        lines.extend(damage_lines(hit_stats["damage_split"]))
        cooldown = pet_ability_cooldown(values)
        if values.get("hit_type", "attack") == "attack":
            lines.append((f"Attacks per second: {1 / cooldown:.2f}", _WHITE))
        else:
            lines.append((f"Cooldown: {cooldown:.2f}s", _WHITE))
        lines.append((f"Crit chance: {_number(values.get('crit_chance', 0))}%", _WHITE))
        lines.append((f"Crit damage: {_number(values.get('crit_damage', 150))}%", _WHITE))
        for effect in getattr(ability, "effects", ()):
            lines.append((f"On hit: {describe_effect(effect)}", _EFFECT))
        from systems.ailments import ailment_types
        for ailment in ailment_types:                                 # "100% chance to poison"
            chance = values.get(f"{ailment}_chance", 0)
            if chance > 0:
                lines.append((f"On hit: {chance:g}% chance to {ailment}", _EFFECT))

    for buff in buffs:
        lines.append((f"Aura: {describe_buff(buff)}", _BUFF))
    return lines

@tooltip_section
def _tt_pet(item, lines):
    """The pet ITEM: its base numbers at this rarity, like a gem item.
    What it really does with your gear and tree: hover it in the hotbar row."""
    if not getattr(item, "is_pet", False) or item.pet_type not in pet_configs:
        return
    values, buffs = pet_base_stats(item.pet_type, item.rarity)
    lines.extend(pet_tooltip_lines(values, buffs))

def pet_live_tooltip_lines(pet):
    """The pet in the hotbar row: everything included."""
    from systems.rarity import rarity_colors
    name = pet.source_item.name if pet.source_item else pet_display_name(pet.pet_type)
    return [(name, rarity_colors.get(pet.rarity, _WHITE))] + pet_tooltip_lines(pet.values, pet.buffs)

@panel_rows("pets")
def _rows_pet_auras(player):
    """Every aura your pets give right now."""
    rows = []
    for pet in player.pets:
        for buff in pet.buffs:
            rows.append((f"{pet_display_name(pet.pet_type)}: {describe_buff(buff)}", _BUFF))
    return rows

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
pet_configs = {}

def register_pet(key, name, sprite, stats, buffs=None, rarity_overrides=None, description=None,
                 name_plural=None, item_name=None, item_sprite=None, item_rarity=None):
    """Define a pet and the item that equips it. Drops go in content/drops.py.

    key              - internal name, e.g. "spider"
    stats            - everything the pet does (ability, movement_speed, crit_chance...)
    buffs            - auras it gives, e.g. [{"stat": "added_fire_spell", "type": "flat", "amount": 20}]
    rarity_overrides - exact values for one rarity, e.g. {rarity_legendary: {"crit_chance": 15}}
                       (use "buffs" as a key to replace its buffs at that rarity)
    description      - one line for the tooltip
    item_name        - name of the pet ITEM (default: "<name> Pet"). Its item key is "<key>_pet".
                       That is also the key its tree uses in register_gem_node().
    item_sprite      - inventory icon (default: same as the pet sprite)
    item_rarity      - the item's default rarity (default: common)
    """
    from systems.items import item_templates

    if key in pet_configs:
        raise ValueError(f"Pet '{key}' is registered twice")
    pet_configs[key] = {
        "sprite": sprite,
        "name": name,
        "name_plural": name_plural or name,
        "stats": stats,
        "buffs": buffs or [],
        "rarity_overrides": rarity_overrides or {},
        "description": description,
    }

    item_key = pet_item_key(key)
    item_templates[item_key] = {
        "kind": "pet",
        "name": item_name or name,
        "sprite": item_sprite or sprite,
        "pet_type": key,
        "rarity": item_rarity or rarity_common,
    }
    return key

def pet_item_key(pet_type):
    """"spider" -> "spider_pet": the item key AND the key of its tree."""
    return pet_type + "_pet"

def roll_pets(weights, count):
    """Pick `count` pet types from a {pet_type: weight} dict, e.g. {"spider": 10, "ghost": 5}."""
    unknown = [k for k in weights if k not in pet_configs]
    if unknown:
        raise KeyError(f"Unknown pet(s) {unknown} in weights. Known pets: {sorted(pet_configs)}")
    return random.choices(list(weights), weights=list(weights.values()), k=count)

def pet_display_name(pet_type, count=1):
    config = pet_configs.get(pet_type, {})
    name = config.get("name", pet_type)
    if count != 1:
        return config.get("name_plural", name)
    return name