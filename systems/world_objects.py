import pygame
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

def draw_depth_sorted(entities):
    for entity, draw_func in sorted(entities, key=lambda pair: pair[0].get_sort_y()):
        draw_func()

world.world_objects = []

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
world_object_configs = {}
