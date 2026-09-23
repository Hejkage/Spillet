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
# ---------------------------------------------------------------
pet_movements = {}

def register_pet_movement(name, move, setup=None):
    if name in pet_movements:
        raise ValueError(f"Pet movement '{name}' is registered twice")
    pet_movements[name] = {"move": move, "setup": setup}

def walk_move(pet, dt, target_x, target_y, dx, dy, distance):
    move_dir = pygame.Vector2(dx, dy).normalize()
    speed = pet.get_stat("speed", 300)
    pet.x += move_dir.x * speed * dt
    pet.y += move_dir.y * speed * dt

def leap_setup(pet):
    pet.leap_timer = 0.0

def leap_move(pet, dt, target_x, target_y, dx, dy, distance):
    from systems.player import begin_leap
    pet.leap_timer -= dt
    if pet.leap_timer <= 0:
        begin_leap(pet, target_x, target_y,
                   pet.get_stat("leap_height", 100),
                   pet.get_stat("leap_time_per_unit", 0.002),
                   pet.get_stat("leap_max_distance", 700),
                   min_distance=pet.get_stat("leap_min_distance", 0),
                   scatter=pet.get_stat("leap_scatter", 0))
        pet.leap_timer = pet.get_stat("leap_cooldown", 0.0)

register_pet_movement("walk", walk_move)
register_pet_movement("leap", leap_move, setup=leap_setup)

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
        self.source_item = None
        self.summon_key = None
        base_angle = random.uniform(0, 360)
        radius = random.uniform(45, 90)
        self.follow_offset = pygame.Vector2(radius, 0).rotate(base_angle)
        self.follow_jitter_seed = random.uniform(0, 1000)

    def get_stat(self, stat_name, default=None):
        return self.stats.get(stat_name, default)
    
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
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
pet_configs = {}

def register_pet(key, name, sprite, stats, name_plural=None,
                 item_name=None, item_sprite=None, item_rarity=None,
                 drop_weight=0.1, drop_rarity=None):
    """Define a pet, the item that equips it, and its drop entry in one call.

    key            - internal name, e.g. "spider"
    stats          - everything the pet does (ability, speed, movement, sound...)
    item_name      - name of the pet ITEM (default: "<name> Pet"). Its item key is "<key>_pet".
    item_sprite    - inventory icon (default: same as the pet sprite)
    item_rarity    - the item's default rarity (default: common)
    drop_weight    - how often the item drops (0 = never, shop-only)
    drop_rarity    - rarity the item has when it DROPS (default: its item_rarity)
    """
    from systems.items import item_templates, make_item
    from systems.rarity import rarity_common
    from systems.drops import DropEntry, pet_group

    if key in pet_configs:
        raise ValueError(f"Pet '{key}' is registered twice")
    pet_configs[key] = {
        "sprite": sprite,
        "name": name,
        "name_plural": name_plural or name,
        "stats": stats,
    }

    item_key = key + "_pet"
    item_templates[item_key] = {
        "kind": "pet",
        "name": item_name or name + " Pet",
        "sprite": item_sprite or sprite,
        "pet_type": key,
        "rarity": item_rarity or rarity_common,
    }

    if drop_weight:
        pet_group.append(DropEntry(lambda k=item_key: make_item(k, rarity=drop_rarity), weight=drop_weight))
    return key

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
