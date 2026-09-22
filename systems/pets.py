import pygame
import random, math
from core.state import app, world
from core.assets import scaled_sprites
from core.sounds import play_sound
from systems.projectiles import Projectile

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Pets/Minions

pet_teleport_distance = 1100

# pet abilities
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

def make_pet_projectile_ability(sprite_name, effects=None):
    def ability(pet, player, dt):
        pet.ability_timer -= dt
        if pet.ability_timer > 0:
            return

        target = nearest_enemy(pet.x, pet.y, pet.ability_range)
        if target is None:
            pet.ability_timer = 0
            return

        direction = pygame.Vector2(target.x - pet.x, target.y - pet.y)
        world.projectiles.append(Projectile(
            sprite_name, pet.x, pet.y, direction,
            speed=pet.ability_projectile_speed,
            damage=pet.ability_damage,
            aoe=1.0,
            from_player=False,
            effects=effects,
        ))
        pet.ability_timer = pet.ability_cooldown
    return ability

class Pet:
    def __init__(self, pet_type, x, y):
        config = pet_configs[pet_type]

        self.pet_type = pet_type
        self.sprite_name = config["sprite"]
        self.stats = dict(config["stats"])
        self.x = x
        self.y = y
        self.follow_distance = 80
        self.ability_cooldown = self.get_stat("ability_cooldown", 3.0)
        self.ability_range = self.get_stat("ability_range", 500)
        self.ability_damage = self.get_stat("ability_damage", 10)
        self.ability_projectile_speed = self.get_stat("ability_projectile_speed", 600)
        self.ability_slow_amount = self.get_stat("ability_slow_amount", 0.3)
        self.ability_slow_duration = self.get_stat("ability_slow_duration", 2.0)
        self.ability_timer = 0
        self.sound_name = self.get_stat("sound")
        self.sound_interval = self.get_stat("sound_interval", 5.0)
        self.sound_volume = self.get_stat("sound_volume", 1.0)
        self.sound_timer = random.uniform(0, self.sound_interval)
        self.leap = None
        self.movement = self.get_stat("movement", "walk")
        self.leap_height = self.get_stat("leap_height", 100)
        self.leap_time_per_unit = self.get_stat("leap_time_per_unit", 0.002)
        self.leap_max_distance = self.get_stat("leap_max_distance", 700)
        self.leap_cooldown = self.get_stat("leap_cooldown", 0.0)
        self.leap_timer = 0.0
        self.leap_min_distance = self.get_stat("leap_min_distance", 0)
        self.leap_scatter = self.get_stat("leap_scatter", 0)

        sprite = scaled_sprites[self.sprite_name]
        self.rect = sprite.get_rect()
        self.source_item = None
        self.summon_key = None
        base_angle = random.uniform(0, 360)
        radius = random.uniform(45, 90)
        self.follow_offset = pygame.Vector2(radius, 0).rotate(base_angle)
        self.follow_jitter_seed = random.uniform(0, 1000)

    def get_stat(self, stat_name, default=None):
        return self.stats.get(stat_name, default)
    
    def pet_update(self, player, dt):
        from systems.player import begin_leap, update_leap
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
            if self.movement == "leap":
                self.leap_timer -= dt
                if self.leap_timer <= 0:
                    begin_leap(self, target_x, target_y, self.leap_height,
                               self.leap_time_per_unit, self.leap_max_distance,
                               min_distance=self.leap_min_distance,
                               scatter=self.leap_scatter)
                    self.leap_timer = self.leap_cooldown
            else:
                move_dir = pygame.Vector2(dx, dy).normalize()
                speed = self.get_stat("speed", 300)
                self.x += move_dir.x * speed * dt
                self.y += move_dir.y * speed * dt
        
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
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
pet_configs = {}
def pet_display_name(pet_type, count=1):
    config = pet_configs.get(pet_type, {})
    name = config.get("name", pet_type)
    if count != 1:
        return config.get("name_plural", name)
    return name
