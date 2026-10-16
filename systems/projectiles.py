import pygame
import math
import random
from core.state import app, world
from core.assets import scaled_sprites
from core.screen import is_near_view
from systems.world_objects import projectile_blocked_at

# region projectiles

world.projectiles = []
world.enemy_projectiles = []
orbit_ring_angle = 0.0
orbit_rehit_cooldown = 0.5
projectile_default_lifetime = 5.0   # seconds; a gem can override it with "lifetime"
projectile_view_scale = 1.5         # projectiles die this many screens from the player
projectile_sprite_angle = {}
projectile_hit_scale = 0.5          # hit radius = half the sprite's short side * aoe * this

class Projectile:
    def __init__(self, sprite_name, x, y, direction, speed, damage=10, aoe=0, hitbox_scale=1, slow_amount=0, slow_duration=0, dot_damage=0, dot_duration=0, effects = None, hit_stats=None, from_player=True, pierce=0,
                    orbit=False, orbit_radius=200, orbit_dir=1, orbit_player=None, lifetime=projectile_default_lifetime, attacker=None):
        self.x = x
        self.y = y
        self.direction = direction.normalize() if direction.length() > 0 else pygame.Vector2(1, 0)
        self.speed = speed
        self.damage = damage
        self.aoe = aoe
        self.sprite_name = sprite_name
        self.hit_stats = hit_stats or {}
        self.alive = True
        self.lifetime = lifetime
        self.effects = list(effects) if effects else []
        if slow_duration > 0:
            self.effects.append({"name": "slow", "duration": slow_duration, "amount": slow_amount})
        if dot_duration > 0:
            self.effects.append({"name": "dot", "duration": dot_duration, "dps": dot_damage, "hit_stats": self.hit_stats})
        self.from_player = from_player
        self.attacker = attacker        # whose stats crit/penetrate with. None = the player
        self.pierce = pierce or 0
        self.pierced = set()
        self.orbit = orbit
        self.orbit_dir = orbit_dir
        self.orbit_player = orbit_player
        self.orbit_order = 0     
        self.spiral_time = 0.5                  
        self.spiral_elapsed = 0.0
        self.orbit_radius = orbit_radius
        self.hit_cooldowns = {}
        
        base_sprite = scaled_sprites[sprite_name]
        base_width, base_height = base_sprite.get_size()

        # What it actually hits with. self.rect is the DRAWN sprite, which rotation
        # inflates (a rotated square's bounding box is up to 41% wider), so hitting
        # off that rect made a big projectile land early and from the side.
        self.hit_radius = min(base_width, base_height) * 0.5 * max(0.01, self.aoe) * projectile_hit_scale

        target_width = int(base_width * self.aoe)
        target_height = int(base_height * self.aoe)
        self.draw_sprite = pygame.transform.scale(base_sprite, (target_width, target_height))
        if not self.orbit:      # orbiting projectiles have no travel direction
            angle = self.direction.as_polar()[1] + projectile_sprite_angle.get(sprite_name, 0)
            self.draw_sprite = pygame.transform.rotate(self.draw_sprite, -angle)
        self.rect = self.draw_sprite.get_rect()

    def projectile_update(self, dt, camera):
        if self.orbit:
            pass
        else:
            self.x += self.direction.x * self.speed * dt
            self.y += self.direction.y * self.speed * dt
        
        if self.hit_cooldowns:
            for e in list(self.hit_cooldowns):
                self.hit_cooldowns[e] -= dt
                if self.hit_cooldowns[e] <= 0:
                    del self.hit_cooldowns[e]

        self.rect.center = camera.apply_camera(self.x, self.y)

        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

        if not self.orbit:
            if self.x < 0 or self.x > world.width or self.y < 0 or self.y > world.height:
                self.alive = False
            if not is_near_view(self.x, self.y, projectile_view_scale):
                self.alive = False

            # the projectile's CENTRE has to reach the object. Checking its drawn
            # rect instead let a big projectile be eaten by something it flew past.
            if projectile_blocked_at(self.x, self.y):
                self.alive = False
    
    def hits_rect(self, rect):
        """Circle against a rect, in screen space. Uses hit_radius, so aoe still
        makes a projectile hit from further out, but honestly."""
        cx, cy = self.rect.center
        nearest_x = min(max(cx, rect.left), rect.right)
        nearest_y = min(max(cy, rect.top), rect.bottom)
        dx, dy = cx - nearest_x, cy - nearest_y
        return dx * dx + dy * dy <= self.hit_radius * self.hit_radius

    def hits_player(self, player):
        from systems.weapons import player_body_radius
        dx = self.x - player.x
        dy = self.y - player.y
        reach = self.hit_radius + player_body_radius
        return dx * dx + dy * dy <= reach * reach


    def projectile_draw(self, camera):
        pos = camera.apply_camera(self.x, self.y)
        self.rect = self.draw_sprite.get_rect(center=pos)        
        app.screen.blit(self.draw_sprite, self.rect)

def update_orbit_ring(dt):
    global orbit_ring_angle

    live = [p for p in world.projectiles if p.orbit and p.alive and p.orbit_player is not None]
    if not live:
        return

    for p in live:
        if p.spiral_elapsed < p.spiral_time:
            p.spiral_elapsed += dt

    arrived = [p for p in live if p.spiral_elapsed >= p.spiral_time]
    travelling = [p for p in live if p.spiral_elapsed < p.spiral_time]

    radius = live[0].orbit_radius
    speed_deg = math.degrees(live[0].speed / radius) * live[0].orbit_dir if radius > 0 else 0
    orbit_ring_angle += speed_deg * dt

    arrived.sort(key=lambda p: p.orbit_order)
    count = len(arrived)
    for slot, p in enumerate(arrived):
        angle = orbit_ring_angle + (360 / count) * slot
        center = pygame.Vector2(p.orbit_player.x, p.orbit_player.y)
        offset = pygame.Vector2(p.orbit_radius, 0).rotate(angle)
        p.x = center.x + offset.x
        p.y = center.y + offset.y

    for p in travelling:
        t = min(1.0, p.spiral_elapsed / p.spiral_time)
        r = p.orbit_radius * t
        angle = orbit_ring_angle + p.orbit_order * 40
        center = pygame.Vector2(p.orbit_player.x, p.orbit_player.y)
        offset = pygame.Vector2(r, 0).rotate(angle)
        p.x = center.x + offset.x
        p.y = center.y + offset.y
#endregion ##################################################################################################################################################################

# region On-hit projectile effects (split, chain)
#
# Both are HIT EFFECTS (systems/status.py): a mod puts them on the hit, and they
# run when the hit lands. They spawn COPIES of the projectile that hit, so the
# copies keep its sprite, speed, damage types, burn chance and every other effect.

def spawn_copy(p, x, y, direction, damage_mult=1.0, size_mult=1.0, effects=None, already_hit=()):
    """A new projectile just like p, starting at (x, y).
    effects      None = the same effects as p
    already_hit  enemies the copy flies through without hitting"""
    copy = Projectile(p.sprite_name, x, y, direction, p.speed, p.damage * damage_mult, p.aoe * size_mult,
                      effects=p.effects if effects is None else effects,
                      hit_stats=p.hit_stats, from_player=p.from_player, pierce=p.pierce, attacker=p.attacker)
    copy.pierced = set(already_hit)
    (world.projectiles if p.from_player else world.enemy_projectiles).append(copy)
    return copy

def without_effect(effects, name):
    return [e for e in effects if e["name"] != name]

def split_on_hit(target, effect, source):
    """Fire `count` smaller copies outwards in a circle from the target."""
    if not isinstance(source, Projectile) or source.orbit:
        return
    count = int(effect.get("count", 0))
    effects = without_effect(without_effect(source.effects, "split"), "chain")   # copies never split or chain
    start = random.uniform(0, 360)                          # a different circle every time
    for i in range(count):
        direction = pygame.Vector2(1, 0).rotate(start + 360 / count * i)
        spawn_copy(source, target.x, target.y, direction,
                   damage_mult=effect.get("damage_mult", 1), size_mult=effect.get("size_mult", 1),
                   effects=effects, already_hit={target})

def chain_on_hit(target, effect, source):
    """Fire one copy at the closest enemy this projectile hasn't hit yet."""
    if not isinstance(source, Projectile) or source.orbit:
        return
    already_hit = set(source.pierced) | {target}
    reach = effect.get("range", 400)
    nearest, nearest_dist = None, reach * reach
    for enemy in world.enemies:
        if enemy.alive and enemy not in already_hit:
            dist = (enemy.x - target.x) ** 2 + (enemy.y - target.y) ** 2
            if dist <= nearest_dist:
                nearest, nearest_dist = enemy, dist
    if nearest is None:
        return
    effects = without_effect(source.effects, "chain")
    if effect.get("count", 0) > 1:                          # chains left after this one
        effects.append({**effect, "count": effect["count"] - 1})
    direction = pygame.Vector2(nearest.x - target.x, nearest.y - target.y)
    spawn_copy(source, target.x, target.y, direction,
               damage_mult=effect.get("damage_mult", 1), effects=effects, already_hit=already_hit)

from systems.status import register_hit_effect
register_hit_effect("split", split_on_hit,
                    describe=lambda e: f"Splits into {int(e.get('count', 0))} projectiles on hit")
register_hit_effect("chain", chain_on_hit,
                    describe=lambda e: f"Chains {int(e.get('count', 0))} times")
#endregion