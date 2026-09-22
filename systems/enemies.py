import pygame
import random
from core.state import app, world
from core.assets import scaled_sprites
from systems.status import status_effect_types
from systems.projectiles import Projectile, orbit_rehit_cooldown
from systems.drops import DropPool
from systems.ground import spawn_drops
from systems.player import begin_leap, leap_height_offset, update_leap
from systems.player import player

# region Enemies

enemy_agro_radius = 900
enemy_deagro_radius =1100
enemy_stop_distance = 45
enemy_seperation_radius = 35
enemy_seperation_weight = 1.4
enemy_contact_radius = 60
enemy_contact_cooldown = 1.0
enemy_cast_time = 0.5
enemy_global_cast_cooldown = 0.4

enemy_grid_cell_size = 128

class SpatialGrid:
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.cells = {}

    def _key(self, x, y):
        return (int(x // self.cell_size), int(y // self.cell_size))

    def rebuild(self, entities):
        self.cells = {}
        for e in entities:
            key = self._key(e.x, e.y)
            bucket = self.cells.get(key)
            if bucket is None:
                self.cells[key] = [e]
            else:
                bucket.append(e)

    def query_nearby(self, x, y):
        cx, cy = self._key(x, y)
        result = []
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                bucket = self.cells.get((gx, gy))
                if bucket:
                    result.extend(bucket)
        return result

    def query_radius(self, x, y, radius):
        cx0 = int((x - radius) // self.cell_size)
        cx1 = int((x + radius) // self.cell_size)
        cy0 = int((y - radius) // self.cell_size)
        cy1 = int((y + radius) // self.cell_size)

        result = []
        for gx in range(cx0, cx1 + 1):
            for gy in range(cy0, cy1 + 1):
                bucket = self.cells.get((gx, gy))
                if bucket:
                    result.extend(bucket)
        return result

enemy_grid = SpatialGrid(enemy_grid_cell_size)

class EnemyAbility():
    def __init__(self, cooldown, ability_range):
        self.cooldown = cooldown
        self.ability_range = ability_range
        self.timer = random.uniform(0.5, 1)

    def tick(self, dt):
        if self.timer > 0:
            self.timer -= dt

    def update(self, enemy, player, dt, dist):
        if self.timer > 0:
            return
        if dist > self.ability_range:
            return
        enemy.begin_cast(self)

    def fire(self, enemy, player, dist):
        pass

class EnemyProjectileAbility(EnemyAbility):
    def __init__(self, cooldown, ability_range, damage, speed, sprite_name, aoe=1.0):
        super().__init__(cooldown, ability_range)
        self.damage = damage
        self.speed = speed
        self.sprite_name = sprite_name
        self.aoe = aoe

    def fire(self, enemy, player, dist):
        direction = pygame.Vector2(player.x - enemy.x, player.y - enemy.y)
        world.enemy_projectiles.append(Projectile(self.sprite_name, enemy.x, enemy.y, direction, speed=self.speed, damage=self.damage, aoe=self.aoe))

enemy_defaults = {
    "base_sprite": None, "sprite_scale": 1.0, "health": 100, "xp_value": 10,
    "move_speed": 120, "contact_damage": 0, "behavior": "melee",
    "attack_range": 400, "cast_cooldown": enemy_global_cast_cooldown,
    "cast_time": enemy_cast_time, "skip_generic_drops": False,
    "leap_range": 500, "leap_height": 120, "leap_time_per_unit": 0.0015,
    "leap_max_distance": 500, "leap_cooldown": 2.5,
    "leap_min_distance": 0, "leap_scatter": 0,
}

enemy_behaviors = {}

def register_behavior(name, movement):
    enemy_behaviors[name] = movement

class Enemy:
    def __init__(self, x, y, enemy_type):
        cfg = {**enemy_defaults, **enemy_configs[enemy_type]}
        for key, value in cfg.items():
            setattr(self, key, value)

        self.x, self.y = x, y
        self.enemy_type = enemy_type
        self.sprite_name = cfg["base_sprite"]
        self.max_health = self.health
        self.drop_pool = cfg.get("drop_pool") or DropPool()
        self.guaranteed_drops = cfg.get("guaranteed_drops", [])
        self.abilities = [f() for f in cfg.get("abilities", [])]
        self.alive = True
        self.slow_multiplier = 1.0
        self.statuses = {}
        self.sprite = self.build_scaled_sprite()
        self.rect = self.sprite.get_rect()
        self.leap = None
        self.leap_timer = random.uniform(0, self.leap_cooldown)
        self.aggroed = False
        self.state = "idle"
        self.contact_timer = 0
        self.casting = False
        self.cast_timer = 0
        self.global_cast_timer = 0
        self.pending_cast = None
    
    def build_scaled_sprite(self):
        base = scaled_sprites[self.sprite_name]
        if self.sprite_scale == 1.0:
            return base
        w, h = base.get_size()
        return pygame.transform.scale(base, (max(1, int(w * self.sprite_scale)), max(1, int(h * self.sprite_scale))))

    def enemy_take_damage(self, amount):
        if not self.alive:
            return
        self.health -= amount
        if self.health <= 0:
            self.alive = False
            player.gain_xp(self.xp_value)
            spawn_drops(self)
            if self.enemy_type == "baby_witch":
                app.start_completed = True
    
    def current_speed(self):
        return self.move_speed * self.slow_multiplier

    def get_sort_y(self):
        return self.y
    
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
    
    def enemy_update_hitbox(self, camera):
        screen_pos = camera.apply_camera(self.x, self.y)
        offset = leap_height_offset(self)                                    
        self.rect.center = (screen_pos[0], screen_pos[1] - int(offset))
    
    def randomize_ability_timers(self):
        for ability in self.abilities:
            ability.timer = random.uniform(0, ability.cooldown)
        self.global_cast_timer = random.uniform(0, self.cast_cooldown)

    def update_ai(self, player, dt):
        if not self.alive:
            return
        
        if update_leap(self, dt):   
            return
        
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if self.aggroed:
            if dist > enemy_deagro_radius:
                self.aggroed = False
                self.state = "idle"
        else:
            if dist <= enemy_agro_radius:
                self.aggroed = True
                self.state = "engaged"
                self.randomize_ability_timers()
        
        if self.casting:
            pass
        elif self.state == "engaged":
            self.update_engaged(player, dt, dx, dy, dist)
        else:
            self.update_idle(dt)

        if self.has_status("silence"):
            self.casting = False
            self.pending_cast = None
        else:
            self.update_cast(player, dt, dist)
            if not self.casting:
                self.update_abilities(player, dt, dist)
                self.update_contact_damage(player, dt, dist)
        if self.state == "engaged":
            for ability in self.abilities:
                ability.tick(dt)    

    def update_contact_damage(self, player, dt, dist):
        if self.contact_timer > 0:
            self.contact_timer -= dt

        if self.contact_damage <= 0:
            return
        if dist <= enemy_contact_radius and self.contact_timer <= 0:
            player.take_damage(self.contact_damage)
            self.contact_timer = enemy_contact_cooldown

    def compute_seperation(self):
        push_x = 0.0
        push_y = 0.0
        for other in enemy_grid.query_nearby(self.x, self.y):
            if other is self or not other.alive:
                continue
            dx = self.x - other.x
            dy = self.y - other.y
            dist_sq = dx * dx + dy * dy
            if dist_sq == 0:
                push_x += 1
                continue
            if dist_sq < enemy_seperation_radius * enemy_seperation_radius:
                dist = dist_sq ** 0.5
                strength = (enemy_seperation_radius - dist) / enemy_seperation_radius
                push_x += (dx / dist) * strength
                push_y += (dy / dist) * strength
        return push_x, push_y

    def update_engaged(self, player, dt, dx, dy, dist):
        move = enemy_behaviors.get(self.behavior, melee_behavior)(self, player, dt, dx, dy, dist)
        if move is None:
            return
        seek_x, seek_y = move
        sep_x, sep_y = self.compute_seperation()
        move_x = seek_x + sep_x * enemy_seperation_weight
        move_y = seek_y + sep_y * enemy_seperation_weight

        length = (move_x * move_x + move_y * move_y) ** 0.5
        if length > 0:
            self.x += (move_x / length) * self.current_speed() * dt
            self.y += (move_y / length) * self.current_speed() * dt
            self.facing = 1 if move_x < 0 else -1

    def update_idle(self, dt):
        pass

    def update_abilities(self, player, dt, dist_to_player):
        ready = sorted(self.abilities, key=lambda a: -a.cooldown)
        for ability in ready:
            ability.update(self, player, dt, dist_to_player)
            if self.casting:
                break
    
    def begin_cast(self, ability):
        if self.casting or self.global_cast_timer > 0:
            return False
        self.casting = True
        self.cast_timer = self.cast_time
        self.pending_cast = ability
        return True
    
    def update_cast(self, player, dt, dist):
        if self.global_cast_timer > 0:
            self.global_cast_timer -= dt

        if not self.casting:
            return
        
        self.cast_timer -= dt
        if self.cast_timer <= 0:
            if self.pending_cast is not None:
                self.pending_cast.fire(self, player, dist)
                self.pending_cast.timer = self.pending_cast.cooldown * random.uniform(0.9, 1.1)
            self.casting = False
            self.pending_cast = None
            self.global_cast_timer = self.cast_cooldown

    def enemy_draw(self):
        app.screen.blit(self.sprite, self.rect)

        #Temporary health bar
        bar_width = self.rect.width
        bar_height = 5
        bar_x = self.rect.left
        bar_y = self.rect.top - 10
        health_ratio = self.health / self.max_health
        pygame.draw.rect(app.screen, (180, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(app.screen, (0, 200, 0), (bar_x, bar_y, int(bar_width * health_ratio), bar_height))

    def try_hit_from_projectile(self, p):
        if not p.alive:
            return

        if p.orbit:
            if self in p.hit_cooldowns:
                return
        else:
            if self in getattr(p, "pierced", ()):
                return

        if self.rect.colliderect(p.rect):
            if p.from_player:
                apply_player_hit(self, p.damage, p.effects, p.hit_stats)
            else:
                self.enemy_take_damage(p.damage)
                for effect in p.effects:
                    params = {k: v for k, v in effect.items() if k not in ("name", "duration")}
                    self.apply_status(effect["name"], effect["duration"], **params)

            if p.orbit:
                if p.pierce > 0:
                    p.hit_cooldowns[self] = orbit_rehit_cooldown
                else:
                    p.alive = False
            else:
                if (getattr(p, "pierce", 0) or 0) > 0:
                    p.pierce -= 1
                    p.pierced.add(self)
                else:
                    p.alive = False
    
    def enemy_is_on_screen(self, camera):
        screen_x, screen_y = camera.apply_camera(self.x, self.y)
        return (-self.rect.width < screen_x < app.screen_width + self.rect.width and -self.rect.height < screen_y < app.screen_height + self.rect.height)
    
def melee_behavior(e, player, dt, dx, dy, dist):
    if dist > enemy_stop_distance and dist > 0:
        return dx / dist, dy / dist
    return 0, 0

def caster_behavior(e, player, dt, dx, dy, dist):
    if dist <= 0:
        return 0, 0
    ux, uy = dx / dist, dy / dist
    if dist > e.attack_range * 1.1:
        return ux, uy
    if dist < e.attack_range * 0.8:
        return -ux, -uy
    return 0, 0

def leaper_behavior(e, player, dt, dx, dy, dist):
    e.leap_timer -= dt
    if dist <= e.leap_range and e.leap_timer <= 0:
        begin_leap(e, player.x, player.y, e.leap_height, e.leap_time_per_unit,
                   e.leap_max_distance, min_distance=e.leap_min_distance,
                   scatter=e.leap_scatter)
        e.leap_timer = e.leap_cooldown
        return None
    return melee_behavior(e, player, dt, dx, dy, dist)

register_behavior("melee",  melee_behavior)
register_behavior("caster", caster_behavior)
register_behavior("leaper", leaper_behavior)

def apply_player_hit(enemy, damage, effects=(), hit_stats=None):
    chance, crit_multiplier = player.crit_stats(hit_stats)

    if chance > 0 and random.uniform(0, 100) < chance:
        damage *= crit_multiplier / 100

    enemy.enemy_take_damage(damage)

    if player.lifesteal > 0:
        player.heal(damage * player.lifesteal / 100)

    for effect in effects:
        params = {k: v for k, v in effect.items() if k not in ("name", "duration")}
        enemy.apply_status(effect["name"], effect["duration"], **params)

    return damage

def process_projectile_hits(projectile_list):
    for p in projectile_list:
        if not p.alive:
            continue
        for e in enemy_grid.query_nearby(p.x, p.y):
            if not e.alive:
                continue
            e.try_hit_from_projectile(p)
            if not p.alive:
                break

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
enemy_configs = {}
