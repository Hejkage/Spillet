import pygame
from core.state import world
from systems.weapons import melee_reach, melee_weapon_sprite
from systems.supports import build_hit_packets
from systems.projectiles import Projectile, projectile_default_lifetime
from systems.facing import face_direction

# region Active Gems
standard_gem_fields = {"always", "name", "cooldown", "attack_time", "action_time", "damage", "aoe", "projectile_speed", "function", "sprite_name", "facing_flip", "weapon_classes", "weapon_tags", "rarity_stats", "speed_stat", "hit_kind",
                    "locks_movement", "lock_duration", "uses_aoe", "action_group", "icon"}

global_action_lockout = 0.2


class ActiveGem:
    def __init__(self, name, base_cooldown, base_damage, base_aoe, base_projectile_speed, gem_function, sprite_name, extra=None, support_gems=None, weapon_class=None):
        self.name = name
        self.base_cooldown = base_cooldown
        self.base_damage = base_damage
        self.base_aoe = base_aoe
        self.base_projectile_speed = base_projectile_speed
        self.timer = 0
        self.gem_function = gem_function
        self.sprite_name = sprite_name
        self.extra = extra if extra is not None else {}
        self.support_gems = support_gems if support_gems is not None else []
         # mods this ability always has (systems/mods.py)
        self.always_mods = []      # from the gem template's "always" list
        self.outside_mods = []     # from the skill tree, uniques...
        self.tags = set()          # what this ability IS (ability_tags) - decides which mods/supports fit
        self.blocked = set()       # what it can't scale with ("blocked" in its template)
        self.facing_flip = 1
        self.weapon_classes = None
        self.speed_stat = None
        self.hit_kind = "projectile"
        self.uses_aoe = True
        self.locks_movement = False
        self.lock_duration = 1.0
        self.action_group = None
        self.weapon_tags = None
        self.icon_name = None     
        self.base_projectiles = 1

    def active_gem_update(self, dt):
        if self.timer > 0:
            self.timer -= dt

    def get_base_effective(self, player):
        # The damage here is the ability's OWN number. The real damage is worked out at the
        # very end of build_hit_packets(), after every support and mod (see finish_hit_damage).

        if self.speed_stat:
            rate = max(0.01, getattr(player, self.speed_stat, 100) / 100)
            cooldown = self.base_cooldown / rate
        else:
            cooldown = self.base_cooldown * max(0.1, 1 - player.cooldown / 100)

        return {
            "damage": self.base_damage,
            "stat": lambda name, default: getattr(player, name, default),   # the player's stats, for finish_hit_damage
            "aoe": self.base_aoe * (player.aoe / 100) if self.uses_aoe else self.base_aoe,
            "speed": self.base_projectile_speed * (player.projectile_speed / 100),
            "cooldown": cooldown,
            "count": self.base_projectiles,
        }

    def get_effective_stats(self, player):
        base = self.get_base_effective(player)

        probe = build_hit_packets(pygame.Vector2(1, 0), base["speed"], base["damage"], base["aoe"], self.sprite_name, self.support_gems, extra=self.mod_extra(base), count=base["count"])

        from systems.damage import damage_split
        per_hit = probe[0]["damage"]
        # what ONE hit is made of, after supports scaled the total
        parts = {t: per_hit * share for t, share in damage_split(probe[0]).items()}
        count = len(probe)
        burst_extra = max((p.get("burst_extra", 0) for p in probe), default=0)
        total_shots = count * (1 + burst_extra)
        cooldown_mult = min((p.get("cooldown_mult", 1.0) for p in probe), default=1.0)
        cooldown = base["cooldown"] * cooldown_mult

        return {
            "damage": per_hit,
            "parts": parts,
            "projectiles": count if self.hit_kind == "projectile" else 0,
            "hit_kind": self.hit_kind,
            "uses_aoe": self.uses_aoe,
            "aoe": probe[0]["aoe"],
            "speed": probe[0]["speed"],
            "cooldown": cooldown,
            "dps": (per_hit * total_shots / cooldown) if cooldown > 0 else 0,
            "dot_damage": probe[0].get("dot_damage", 0),
            "dot_duration": probe[0].get("dot_duration", 0),
            "hit_stats": probe[0],
            "orbit_range": max((p.get("orbit_radius", 0) for p in probe), default=0),
            "arc": self.extra.get("arc", 0),
            "range": (melee_reach(player, melee_weapon_sprite(self.sprite_name), self.extra.get("range_mult", 1.0), probe[0]["aoe"] if self.extra.get("aoe_scales_range", False) else 1.0) if self.hit_kind == "melee" else 0),
        }

    def mod_extra(self, base):
        """self.extra plus the mod lists build_hit_packets() reads."""
        extra = dict(self.extra)
        extra["_always"] = self.always_mods
        extra["_mods"] = self.outside_mods
        extra["_stat"] = base["stat"]             # build_hit_packets() works out the final damage with these
        return extra

    def try_cast(self, player, target_pos, camera):
        if self.timer > 0:
            return
        if player.is_action_busy(self.action_group):
            return

        base = self.get_base_effective(player)

        probe = build_hit_packets(pygame.Vector2(1, 0), base["speed"], base["damage"], base["aoe"], self.sprite_name, self.support_gems, extra=self.mod_extra(base))
        cooldown_mult = min((p.get("cooldown_mult", 1.0) for p in probe), default=1.0)
        self.timer = base["cooldown"] * cooldown_mult

        player.begin_action(self.action_group, max(global_action_lockout, self.action_time))

        if self.locks_movement:
            player.begin_action_lock(self.timer * self.lock_duration)

        extra = self.mod_extra(base)
        extra["_interval"] = self.timer
        extra["_count"] = base["count"]

        self.gem_function(player, target_pos, camera, base["damage"], base["aoe"], base["speed"], self.sprite_name, self.support_gems, extra=extra, facing_flip=self.facing_flip)

def template_hit_type(t):
    """"attack" or "spell" - every gem template says which with "hit_type"."""
    return t.get("hit_type", "attack")

def template_speed_stat(t):
    """What makes this ability faster: an ATTACK uses attack speed, a SPELL uses
    cooldown reduction. A gem can override it with its own "speed_stat"."""
    if "speed_stat" in t:
        return t["speed_stat"]
    return "attack_speed" if template_hit_type(t) == "attack" else None

def template_uses_aoe(t):
    if "uses_aoe" in t:
        return t["uses_aoe"]
    return (t.get("hit_kind", "projectile") == "projectile"
            or t.get("aoe_scales_range", False)
            or t.get("aoe_scales_arc", False))

def ability_tags(t):
    """Everything an ability IS, worked out from its template (tags: systems/tags.py).
    Only what can't be worked out goes in the template's own "tags"."""
    from systems.tags import with_groups
    tags = set(t.get("tags", ()))
    tags.add(template_hit_type(t))                                          # attack / spell
    tags.add("melee" if t.get("hit_kind", "projectile") == "melee" else "projectile")
    tags |= set(t.get("damage_split") or {t.get("damage_type", "physical"): 1})   # its damage types
    tags.add("damage")
    if template_uses_aoe(t):
        tags.add("aoe")
    if "dot_duration" in t or any("dot_damage" in row for row in t.get("rarity_stats", {}).values()):
        tags.add("dot")
    tags |= set(t.get("weapon_tags", ()))                                   # caster / melee / ranged
    return with_groups(tags)                                                # fire -> also elemental

def ability_blocked(t):
    """The template's "blocked" set, with groups opened up: {"elemental"} -> + fire, frost, nature."""
    from systems.tags import with_members
    return with_members(t.get("blocked", ()))

def build_active_gem(t, supports, gem_stats=None, outside_mods=()):
        extra = {k: v for k, v in t.items() if k not in standard_gem_fields}
        extra["hit_type"] = template_hit_type(t)
        extra["tags"] = ability_tags(t)
        extra["blocked"] = ability_blocked(t)

        rolled = gem_stats or {}

        def val(stat, default):
            return rolled.get(stat, t.get(stat, default))

        damage   = val("damage", 10)
        aoe      = val("aoe", 1)
        speed    = val("projectile_speed", 600)
        cooldown = val("attack_time", None)
        if cooldown is None:
            cooldown = val("cooldown", 0.6)

        if "attack_time" in t and "cooldown" in t:
            print(f"Warning: gem template '{t.get('name')}' sets both attack_time and cooldown")
        if "dot_damage" in rolled:
            extra["dot_damage"] = rolled["dot_damage"]
        if "dot_duration" in rolled:
            extra["dot_duration"] = rolled["dot_duration"]
        if "crit_chance" in rolled:
            key = "spell_crit_chance" if extra["hit_type"] == "spell" else "attack_crit_chance"
            extra[key] = rolled["crit_chance"]
        if "crit_damage" in rolled:
            extra["crit_damage"] = rolled["crit_damage"]
        from systems.ailments import ailment_stats
        for key, *_ in ailment_stats:                  # "burn_chance" in rarity_stats -> on the hit
            if key in rolled:
                extra[key] = rolled[key]

        gem = ActiveGem(
            t["name"], cooldown, damage, aoe, speed,
            t["function"], t["sprite_name"], extra=extra, support_gems=supports
        )
        gem.facing_flip = t.get("facing_flip", 1)
        gem.speed_stat = template_speed_stat(t)
        gem.hit_kind = t.get("hit_kind", "projectile")
        gem.uses_aoe = template_uses_aoe(t)
        gem.locks_movement = t.get("locks_movement", False)
        gem.lock_duration = t.get("lock_duration", 1.0)
        gem.action_group = t.get("action_group", "action")
        gem.weapon_classes = t.get("weapon_classes")
        gem.weapon_tags = t.get("weapon_tags")
        gem.icon_name = t.get("icon")
        gem.action_time = t.get("action_time", t.get("swing_time", 0))
        gem.base_projectiles = int(val("projectiles", 1))
        gem.always_mods = list(t.get("always", ()))        # what this gem always does
        gem.outside_mods = list(outside_mods)              # skill tree, uniques
        gem.tags = extra["tags"]                           # decides which mods / supports fit
        gem.blocked = extra["blocked"]
        return gem


pending_bursts = []
class PendingBurst:
    def __init__(self, player, projectile_data, remaining, interval):
        self.player = player
        self.projectile_data = projectile_data
        self.remaining = remaining
        self.interval = interval
        self.timer = interval

    def update(self, dt):
        self.timer -= dt
        while self.timer <= 0 and self.remaining > 0:
            self.timer += self.interval
            self.remaining -= 1
            spawn_projectiles(self.player, self.projectile_data)

orbit_spawn_counter = 0

def spawn_projectiles(player, projectile_data):
    global orbit_spawn_counter

    for p in projectile_data:
        proj = Projectile(
            p["sprite"], player.x, player.y, p["direction"], p["speed"], p["damage"], p["aoe"],
            dot_damage=p.get("dot_damage", 0),
            dot_duration=p.get("dot_duration", 0),
            effects=p.get("effects", ()),     # effects a mod or a gem attached
            hit_stats=p,
            pierce=p.get("pierce", 0),
            orbit=p.get("orbit", False),
            orbit_radius=p.get("orbit_radius", 200),
            orbit_dir=p.get("orbit_dir", 1),
            orbit_player=player,
            lifetime=p.get("lifetime", projectile_default_lifetime),
        )

        if proj.orbit:
            proj.orbit_order = orbit_spawn_counter
            orbit_spawn_counter += 1

            orbiting = [x for x in world.projectiles if x.orbit and x.alive]
            if len(orbiting) >= 25:
                oldest = min(orbiting, key=lambda x: x.orbit_order)
                oldest.alive = False
                world.projectiles.remove(oldest)

        world.projectiles.append(proj)

def cast_projectile_spell(player, target_pos, camera, damage, aoe, speed, sprite_name, support_gems, extra=None, facing_flip=1):
    player_screen_pos = pygame.Vector2(camera.apply_camera(player.x, player.y))
    base_direction = pygame.Vector2(target_pos) - player_screen_pos

    face_direction(player, base_direction.x, base_direction.y, flip=facing_flip)

    projectile_data = build_hit_packets(base_direction, speed, damage, aoe, sprite_name, support_gems, extra=extra)
    spawn_projectiles(player, projectile_data)

    burst_extra = max((p.get("burst_extra", 0) for p in projectile_data), default=0)
    if burst_extra > 0:
        interval = projectile_data[0].get("burst_interval", 0.05)
        pending_bursts.append(PendingBurst(player, projectile_data, burst_extra, interval))

def shoot_projectile_gun(player, target_pos, camera, damage, aoe, speed, sprite_name, support_gems, extra=None, facing_flip=1):
    player_screen_pos = pygame.Vector2(camera.apply_camera(player.x, player.y))
    base_direction = pygame.Vector2(target_pos) - player_screen_pos

    face_direction(player, base_direction.x, base_direction.y, flip=facing_flip)

    projectile_data = build_hit_packets(base_direction, speed, damage, aoe, sprite_name, support_gems, extra=extra)
    spawn_projectiles(player, projectile_data)

    burst_extra = max((p.get("burst_extra", 0) for p in projectile_data), default=0)
    if burst_extra > 0:
        interval = projectile_data[0].get("burst_interval", 0.05)
        pending_bursts.append(PendingBurst(player, projectile_data, burst_extra, interval))
#endregion ##################################################################################################################################################################

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
active_gem_templates = {}
basic_attack_templates = {}
basic_attacks_by_weapon_key = {}
basic_attacks_by_weapon = {}


# ---------------------------------------------------------------
# ONE-CALL REGISTRATION
#
# Adding an active gem used to mean editing THREE separate places:
#   1. active_gem_templates  - the mechanic
#   2. item_templates        - the item that grants it
#
# register_active_gem() does all three from a single block, so a new
# gem is one edit in content/gems.py and nothing else.
# ---------------------------------------------------------------

def register_active_gem(key, item_sprite=None, item_rarity=None, **template):
    """Define a gem, the item that grants it, and its drop entry in one call.

    key          - internal name, e.g. "shotgun_blast"
    item_sprite  - inventory icon; defaults to the gem's own sprite_name
    **template   - everything active_gem_templates normally takes
    """
    from systems.items import item_templates
    from systems.rarity import rarity_common

    name = template.get("name", key.replace("_", " ").title())
    template["name"] = name
    active_gem_templates[key] = template

    item_key = key + "_gem"
    item_templates[item_key] = {
        "kind": "active_gem",
        "name": name + " Gem",
        "sprite": item_sprite or template["sprite_name"],
        "template_key": key,
        "rarity": item_rarity or rarity_common,
    }
    return key
