"""HIT FLASH - tints a sprite for a moment when it is hit. Works on anything that is drawn.

    flash(enemy)                                  # the normal red hit flash
    flash(player, color=(255, 255, 255))          # a white flash
    flash(boss, color=(120, 200, 255), duration=0.4, strength=0.8)   # a long blue one

It is drawn automatically by facing_surface() in systems/facing.py, so everything
that uses facing_surface() can flash - player, enemies, and anything you add later.
Anything else can call flash_surface(entity, sprite) right before it blits.

No extra art needed: the tint is made from the sprite itself.
"""
import time

hit_flash_color = (255, 40, 40)    # red
hit_flash_time = 0.15              # seconds
hit_flash_strength = 0.65          # 0 = no tint, 1 = solid colour

def flash(entity, color=None, duration=None, strength=None):
    duration = hit_flash_time if duration is None else duration
    entity.flash_color = hit_flash_color if color is None else color
    entity.flash_duration = duration
    entity.flash_strength = hit_flash_strength if strength is None else strength
    entity.flash_until = time.monotonic() + duration

def flash_surface(entity, sprite):
    """The sprite with the entity's flash on it, or the sprite unchanged if it isn't flashing."""
    until = getattr(entity, "flash_until", 0)
    left = until - time.monotonic()
    if left <= 0:
        return sprite
    import pygame
    # strongest right after the hit, fading to nothing
    amount = entity.flash_strength * (left / entity.flash_duration)
    keep = int(255 * (1 - amount))
    r, g, b = entity.flash_color
    tinted = sprite.copy()
    tinted.fill((keep, keep, keep), special_flags=pygame.BLEND_RGB_MULT)          # darken the original...
    tinted.fill((int(r * amount), int(g * amount), int(b * amount)),
                special_flags=pygame.BLEND_RGB_ADD)                               # ...and add the colour
    return tinted                                                                 # (see-through parts stay see-through)
