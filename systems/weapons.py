import pygame
from core.assets import sprites

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Weapon geometry #########################################################################

player_body_radius = 22          

weapon_geometry_configs = {
    "melee_attack_sprite": {"grip": 20, "hand_offset_y": 7,"range_scale": 1.0},
}

default_grip_ratio = 0.25
default_hand_offset_y = 10
default_range_scale = 1.0

_weapon_geometry_cache = {}

def get_weapon_geometry(sprite_name):
    geom = _weapon_geometry_cache.get(sprite_name)
    if geom is not None:
        return geom

    sprite = sprites.get(sprite_name)
    if sprite is None:
        geom = {"length": 0, "height": 0, "grip": 0, "reach": 0, "hand_offset_y": 0}
    else:
        length = sprite.get_width()
        config = weapon_geometry_configs.get(sprite_name, {})
        grip = config.get("grip", length * default_grip_ratio)
        range_scale = config.get("range_scale", default_range_scale)
        geom = {"length": length, "height": sprite.get_height(), "grip": grip, "reach": max(1.0, (length - grip) * range_scale), "hand_offset_y": config.get("hand_offset_y", default_hand_offset_y),}

    _weapon_geometry_cache[sprite_name] = geom
    return geom

_flipped_sprite_cache = {}

def get_flipped_sprite(sprite_name):
    flipped = _flipped_sprite_cache.get(sprite_name)
    if flipped is None:
        flipped = pygame.transform.flip(sprites[sprite_name], False, True)
        _flipped_sprite_cache[sprite_name] = flipped
    return flipped

_swing_sprite_cache = {}

def get_swing_sprite(sprite_name, scale, flip_v):
    scale = round(scale, 2)
    if scale <= 0:
        scale = 0.01
    key = (sprite_name, scale, flip_v)
    cached = _swing_sprite_cache.get(key)
    if cached is not None:
        return cached

    base = sprites.get(sprite_name)
    if base is None:
        _swing_sprite_cache[key] = None
        return None

    surf = base
    if scale != 1.0:
        w = max(1, int(base.get_width() * scale))
        h = max(1, int(base.get_height() * scale))
        surf = pygame.transform.smoothscale(base, (w, h))
    if flip_v:
        surf = pygame.transform.flip(surf, False, True)

    _swing_sprite_cache[key] = surf
    return surf

def melee_weapon_sprite(fallback):
    from systems.items import equipment
    weapon = equipment.main_slots.get("weapon")
    if weapon is None:
        return fallback

    name = getattr(weapon, "swing_sprite_name", None)
    if name and name in sprites:
        return name
    return fallback

def melee_reach(player, sprite_name, range_mult=1.0, aoe=1.0):
    geom = get_weapon_geometry(sprite_name)
    base = player_body_radius + geom["reach"] + player.attack_range
    return base * range_mult

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
weapon_class_configs = {}
def weapon_class_tags(weapon_class):
    config = weapon_class_configs.get(weapon_class)
    return config["tags"] if config else set()
