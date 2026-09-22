import pygame
import math
from core.state import app, world
from core.assets import scaled_sprites

# region projectiles

world.projectiles = []
world.enemy_projectiles = []
orbit_ring_angle = 0.0
orbit_rehit_cooldown = 0.5

class Projectile:
    def __init__(self, sprite_name, x, y, direction, speed, damage=10, aoe=0, hitbox_scale=1, slow_amount=0, slow_duration=0, dot_damage=0, dot_duration=0, effects = None, hit_stats=None, from_player=True, pierce=0,
                orbit=False, orbit_radius=200, orbit_dir=1, orbit_player=None,):
        self.x = x
        self.y = y
        self.direction = direction.normalize() if direction.length() > 0 else pygame.Vector2(1, 0)
        self.speed = speed
        self.damage = damage
        self.aoe = aoe
        self.sprite_name = sprite_name
        self.hit_stats = hit_stats or {}
        self.alive = True
        self.lifetime = 5.0
        self.effects = list(effects) if effects else []
        if slow_duration > 0:
            self.effects.append({"name": "slow", "duration": slow_duration, "amount": slow_amount})
        if dot_duration > 0:
            self.effects.append({"name": "dot", "duration": dot_duration, "dps": dot_damage})
        self.from_player = from_player
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

        target_width = int(base_width * self.aoe)
        target_height = int(base_height * self.aoe)
        self.draw_sprite = pygame.transform.scale(base_sprite, (target_width, target_height))
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

            for o in world.world_objects:
                if o.blocks_projectiles and self.rect.colliderect(o.rect):
                    self.alive = False
                    break
    
    def hits_player(self, player):
        px, py = player.x, player.y
        dx = self.x - px
        dy = self.y - py
        hit_radius = 20 + max(self.rect.width, self.rect.height) * 0.3
        return (dx * dx + dy * dy) ** 0.5 <= hit_radius


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
