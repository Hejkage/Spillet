"""Which way an entity is facing, and which sprite that means.

Anything that moves or aims calls face_direction() with that direction.
Anything that draws calls facing_sprite_name() / facing_surface().

An entity just needs these attributes - no base class, no inheritance:
    sprite_name       - front/default sprite (required)
    back_sprite_name  - optional; used when facing away from the camera
    facing            -  1 = right, -1 = left          (set by face_direction)
    facing_y          -  1 = toward camera, -1 = away  (set by face_direction)

All art is drawn facing right, so facing == -1 is the mirrored case.
"""
import pygame

def face_direction(entity, dx, dy, flip=1):
    """Point entity at (dx, dy). Screen/world space, so dy < 0 is up/away.

    dx == 0 keeps the current horizontal facing, so moving or aiming straight
    up or down doesn't snap the sprite sideways.
    """
    if dx != 0:
        entity.facing = (1 if dx > 0 else -1) * flip
    entity.facing_y = -1 if dy < 0 else 1

def facing_sprite_name(entity):
    """Which sprite to draw for the entity's current vertical facing."""
    back = getattr(entity, "back_sprite_name", None)
    if back and getattr(entity, "facing_y", 1) < 0:
        return back
    return entity.sprite_name

def facing_surface(entity, sprite):
    """Mirror a sprite if the entity faces left."""
    if getattr(entity, "facing", 1) == -1:
        return pygame.transform.flip(sprite, True, False)
    return sprite