import pygame
from core.state import world
from systems.weapons import melee_reach, melee_weapon_sprite
from systems.supports import apply_support_gems
from systems.projectiles import Projectile

# region Active Gems
standard_gem_fields = {"name", "cooldown", "attack_time", "damage", "aoe", "projectile_speed", "function", "sprite_name", "facing_flip", "weapon_classes", "weapon_tags", "support_tags", "damage_scaling", "rarity_stats", "speed_stat", "hit_kind",
                    "locks_movement", "lock_duration", "uses_aoe", "action_group", "icon"}
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
        self.facing_flip = 1
        self.weapon_classes = None
        self.damage_scaling = []
        self.speed_stat = None
        self.hit_kind = "projectile"
        self.uses_aoe = True
        self.locks_movement = False
        self.lock_duration = 1.0
        self.action_group = None
        self.weapon_tags = None
        self.icon_name = None 

    def active_gem_update(self, dt):
        if self.timer > 0:
            self.timer -= dt

    def get_base_effective(self, player):
        damage_mult = 1.0 + sum((getattr(player, s, 100) - 100) / 100 for s in self.damage_scaling)

        if self.speed_stat:
            rate = max(0.01, getattr(player, self.speed_stat, 100) / 100)
            cooldown = self.base_cooldown / rate
        else:
            cooldown = self.base_cooldown * max(0.1, 1 - player.cooldown / 100)

        return {
            "damage": self.base_damage * damage_mult,
            "aoe": self.base_aoe * (player.aoe / 100),
            "speed": self.base_projectile_speed * (player.projectile_speed / 100),
            "cooldown": cooldown,
        }

    def get_effective_stats(self, player):
        base = self.get_base_effective(player)

        probe = apply_support_gems(pygame.Vector2(1, 0), base["speed"], base["damage"], base["aoe"], self.sprite_name, self.support_gems, extra=self.extra)

        per_hit = probe[0]["damage"]
        count = len(probe)
        burst_extra = max((p.get("burst_extra", 0) for p in probe), default=0)
        total_shots = count * (1 + burst_extra)
        cooldown_mult = min((p.get("cooldown_mult", 1.0) for p in probe), default=1.0)
        cooldown = base["cooldown"] * cooldown_mult

        return {
            "damage": per_hit,
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

    def try_cast(self, player, target_pos, camera):
        if self.timer > 0:
            return
        if player.is_action_busy(self.action_group):
            return

        base = self.get_base_effective(player)

        probe = apply_support_gems(pygame.Vector2(1, 0), base["speed"], base["damage"], base["aoe"], self.sprite_name, self.support_gems, extra=self.extra)
        cooldown_mult = min((p.get("cooldown_mult", 1.0) for p in probe), default=1.0)
        self.timer = base["cooldown"] * cooldown_mult

        player.begin_action(self.action_group, self.timer)

        if self.locks_movement:
            player.begin_action_lock(self.timer * self.lock_duration)

        extra = dict(self.extra)
        extra["_interval"] = self.timer

        self.gem_function(player, target_pos, camera, base["damage"], base["aoe"], base["speed"], self.sprite_name, self.support_gems, extra=extra, facing_flip=self.facing_flip)

def template_uses_aoe(t):
    if "uses_aoe" in t:
        return t["uses_aoe"]
    return (t.get("hit_kind", "projectile") == "projectile"
            or t.get("aoe_scales_range", False)
            or t.get("aoe_scales_arc", False))

def build_active_gem(t, supports, gem_stats=None):
        extra = {k: v for k, v in t.items() if k not in standard_gem_fields}

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
            extra["crit_chance"] = rolled["crit_chance"]
        if "crit_damage" in rolled:
            extra["crit_damage"] = rolled["crit_damage"]

        gem = ActiveGem(
            t["name"], cooldown, damage, aoe, speed,
            t["function"], t["sprite_name"], extra=extra, support_gems=supports
        )
        gem.facing_flip = t.get("facing_flip", 1)
        gem.damage_scaling = t.get("damage_scaling", [])
        gem.speed_stat = t.get("speed_stat")
        gem.hit_kind = t.get("hit_kind", "projectile")
        gem.uses_aoe = template_uses_aoe(t)
        gem.locks_movement = t.get("locks_movement", False)
        gem.lock_duration = t.get("lock_duration", 1.0)
        gem.action_group = t.get("action_group", "action")
        gem.weapon_classes = t.get("weapon_classes")
        gem.weapon_tags = t.get("weapon_tags")
        gem.icon_name = t.get("icon")
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
            hit_stats=p,
            pierce=p.get("pierce", 0),
            orbit=p.get("orbit", False),
            orbit_radius=p.get("orbit_radius", 200),
            orbit_dir=p.get("orbit_dir", 1),
            orbit_player=player,
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

    if base_direction.x > 0:
        player.facing = -1 * facing_flip
    elif base_direction.x < 0:
        player.facing = 1 * facing_flip

    projectile_data = apply_support_gems(base_direction, speed, damage, aoe, sprite_name, support_gems, extra=extra)
    spawn_projectiles(player, projectile_data)

    burst_extra = max((p.get("burst_extra", 0) for p in projectile_data), default=0)
    if burst_extra > 0:
        interval = projectile_data[0].get("burst_interval", 0.05)
        pending_bursts.append(PendingBurst(player, projectile_data, burst_extra, interval))

def shoot_projectile_gun(player, target_pos, camera, damage, aoe, speed, sprite_name, support_gems, extra=None, facing_flip=1):
    player_screen_pos = pygame.Vector2(camera.apply_camera(player.x, player.y))
    base_direction = pygame.Vector2(target_pos) - player_screen_pos

    if base_direction.x > 0:
        player.facing = -1 * facing_flip
    elif base_direction.x < 0:
        player.facing = 1 * facing_flip

    projectile_data = apply_support_gems(base_direction, speed, damage, aoe, sprite_name, support_gems, extra=extra)
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
#   3. active_gem_group      - so it can actually drop
#
# register_active_gem() does all three from a single block, so a new
# gem is one edit in content/gems.py and nothing else.
# ---------------------------------------------------------------

def register_active_gem(key, drop_weight=5, item_sprite=None, item_rarity=None, **template):
    """Define a gem, the item that grants it, and its drop entry in one call.

    key          - internal name, e.g. "shotgun_blast"
    drop_weight  - how often it drops (0 = never drops, shop-only)
    item_sprite  - inventory icon; defaults to the gem's own sprite_name
    **template   - everything active_gem_templates normally takes
    """
    from systems.items import item_templates, make_item
    from systems.rarity import rarity_common, roll_rarity
    from systems.drops import DropEntry, active_gem_group

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

    if drop_weight:
        active_gem_group.append(
            DropEntry(lambda k=item_key: make_item(k, rarity=roll_rarity()), weight=drop_weight)
        )
    return key
