import math
import pygame
import random
from core.state import app, world
from core.assets import scaled_sprites

# region World Objects

class WorldObject:
    def __init__(self, x, y, object_type):
        config = world_object_configs[object_type]

        self.x = x
        self.y = y
        self.object_type = object_type
        self.sprite_name = config["sprite"]
        self.blocks_movement = config["blocks_movement"]
        self.blocks_projectiles = config["blocks_projectiles"]

        hitbox_width, hitbox_height = config.get("hitbox_size", (40, 40))
        self.hitbox_offset = config.get("hitbox_offset", (0, 0))

        self.rect = pygame.Rect(0, 0, hitbox_width, hitbox_height)
        offset_x, offset_y = self.hitbox_offset
        self.rect.center = (self.x + offset_x, self.y + offset_y)

        self.sprite_rect = scaled_sprites[self.sprite_name].get_rect()
        self.sprite_rect.center = (self.x, self.y)
        self.linked_container = None   
        self.use_radius = 120         

    def world_object_update_hitbox(self, camera):
        offset_x, offset_y = self.hitbox_offset
        self.rect.center = camera.apply_camera(self.x + offset_x, self.y + offset_y)
        self.sprite_rect.center = camera.apply_camera(self.x, self.y)

    def world_object_draw(self):
        sprite = scaled_sprites[self.sprite_name]
        app.screen.blit(sprite, self.sprite_rect)
    
    def get_sort_y(self):
        offset_x, offset_y = self.hitbox_offset
        return self.y + offset_y

def world_rect_at(obj):
    offset_x, offset_y = obj.hitbox_offset
    half_w = obj.rect.width / 2
    half_h = obj.rect.height / 2
    center_x = obj.x + offset_x
    center_y = obj.y + offset_y
    return pygame.Rect(center_x - half_w, center_y - half_h, obj.rect.width, obj.rect.height)

def move_with_collision(entity, dx, dy, radius):
    """Move anything with .x/.y (player, enemy, pet, npc) by (dx, dy).
    Blocked by world objects with blocks_movement. Each axis is tried on its own,
    so the entity slides along a wall instead of stopping dead."""
    blockers = [world_rect_at(o) for o in world.world_objects if o.blocks_movement]

    new_x = entity.x + dx
    box_x = pygame.Rect(new_x - radius, entity.y - radius, radius * 2, radius * 2)
    if not any(r.colliderect(box_x) for r in blockers):
        entity.x = new_x

    new_y = entity.y + dy
    box_y = pygame.Rect(entity.x - radius, new_y - radius, radius * 2, radius * 2)
    if not any(r.colliderect(box_y) for r in blockers):
        entity.y = new_y

def nearest_free_point(from_x, from_y, x, y, radius):
    """Return (x, y) if an entity of this radius fits there. If it is inside a blocking
    world object, walk back towards (from_x, from_y) until the first free spot."""
    blockers = [world_rect_at(o) for o in world.world_objects if o.blocks_movement]

    def is_free(px, py):
        box = pygame.Rect(px - radius, py - radius, radius * 2, radius * 2)
        return not any(r.colliderect(box) for r in blockers)

    if is_free(x, y):
        return x, y
    dist = ((x - from_x) ** 2 + (y - from_y) ** 2) ** 0.5
    step = 4
    for i in range(1, int(dist // step) + 1):
        t = 1 - (i * step) / dist
        px = from_x + (x - from_x) * t
        py = from_y + (y - from_y) * t
        if is_free(px, py):
            return px, py
    return from_x, from_y

# ---------------------------------------------------------------
# FORMATIONS - a shape made of world objects, placed around one point.
# A formation function gets (area, object_type, x, y, **settings) and calls
# area.add(...) itself, so it can do anything a build function can.
# ---------------------------------------------------------------
formation_shapes = {}

def register_formation(name, fn):
    formation_shapes[name] = fn

def cluster_formation(area, object_type, x, y, count=6, radius=110, **kw):
    """A loose heap - a few big rocks huddled together."""
    for _ in range(count):
        angle = math.radians(random.uniform(0, 360))
        dist = random.uniform(0, radius)
        area.add(object_type, x + math.cos(angle) * dist, y + math.sin(angle) * dist)

def ring_formation(area, object_type, x, y, count=10, radius=200, jitter=20, **kw):
    """A circle with a gap in the middle - a clearing, a stone circle."""
    for i in range(count):
        angle = math.radians(360 / count * i)
        r = radius + random.uniform(-jitter, jitter)
        area.add(object_type, x + math.cos(angle) * r, y + math.sin(angle) * r)

def vein_formation(area, object_type, x, y, count=8, step=70, jitter=35, **kw):
    """A wandering line - an outcrop, a fallen wall, a hedge."""
    angle = random.uniform(0, 360)
    for _ in range(count):
        area.add(object_type, x, y)
        angle += random.uniform(-35, 35)
        rad = math.radians(angle)
        x += math.cos(rad) * step + random.uniform(-jitter, jitter)
        y += math.sin(rad) * step + random.uniform(-jitter, jitter)

def clump_formation(area, object_type, x, y, count=14, radius=260, tightness=2.0, **kw):
    """Dense in the middle, thinning out - a thicket or boulder field."""
    for _ in range(count):
        angle = math.radians(random.uniform(0, 360))
        dist = radius * (random.random() ** tightness)
        area.add(object_type, x + math.cos(angle) * dist, y + math.sin(angle) * dist)

register_formation("cluster", cluster_formation)
register_formation("ring",    ring_formation)
register_formation("vein",    vein_formation)
register_formation("clump",   clump_formation)

def draw_depth_sorted(entities):
    for entity, draw_func in sorted(entities, key=lambda pair: pair[0].get_sort_y()):
        draw_func()

world.world_objects = []

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
world_object_configs = {}
