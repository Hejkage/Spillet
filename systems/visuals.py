"""VISUALS - a sprite shown for a moment: swipe marks on the player, a flash, a puff.

    spawn_visual("swipe_marks_sprite", follow=player, duration=0.25)
    spawn_visual("puff_sprite", x=500, y=300, duration=0.4)
    spawn_visual("swipe_marks_sprite", follow=player, offset=12, spin=40)   # a bit random

follow    anything with .x / .y - the sprite stays on it while it moves
x, y      a fixed spot in the world instead
duration  seconds it is shown. It fades out over the last half of that time.
scale     1 = the sprite's own size
offset    moves it up to this many pixels in a random direction (0 = exact spot)
spin      turns it a random amount between -spin and +spin degrees (0 = upright)
angle     a fixed turn in degrees, added before the random spin

Only for looks: it never deals damage or blocks anything.
A sprite that doesn't exist yet is skipped, so you can add the art later.
"""
import math
import random
import pygame
from core.assets import scaled_sprites
from core.state import app

visuals = []

class Visual:
    def __init__(self, sprite_name, follow, x, y, duration, scale, offset, angle):
        self.follow = follow
        self.x, self.y = x, y
        self.duration = duration
        self.timer = duration

        # random nudge, picked once so it doesn't jitter every frame
        direction = random.uniform(0, math.tau)
        distance = random.uniform(0, offset)
        self.offset_x = math.cos(direction) * distance
        self.offset_y = math.sin(direction) * distance

        # scale and turn the sprite once, here, instead of every frame
        sprite = scaled_sprites[sprite_name]
        if scale != 1.0:
            w, h = sprite.get_size()
            sprite = pygame.transform.scale(sprite, (max(1, int(w * scale)), max(1, int(h * scale))))
        if angle:
            sprite = pygame.transform.rotate(sprite, angle)
        self.sprite = sprite

    def position(self):
        if self.follow is not None:
            return self.follow.x + self.offset_x, self.follow.y + self.offset_y
        return self.x + self.offset_x, self.y + self.offset_y

def spawn_visual(sprite_name, follow=None, x=0, y=0, duration=0.25, scale=1.0,
                 offset=0, spin=0, angle=0):
    if not sprite_name or sprite_name not in scaled_sprites:
        return
    turn = angle + (random.uniform(-spin, spin) if spin else 0)
    visuals.append(Visual(sprite_name, follow, x, y, duration, scale, offset, turn))

def update_visuals(dt):
    for v in visuals:
        v.timer -= dt
    visuals[:] = [v for v in visuals if v.timer > 0]

def draw_visuals(camera):
    for v in visuals:
        sprite = v.sprite
        fade = min(1.0, v.timer / (v.duration / 2)) if v.duration > 0 else 1.0
        if fade < 1.0:
            sprite = sprite.copy()
            sprite.set_alpha(int(255 * fade))
        app.screen.blit(sprite, sprite.get_rect(center=camera.apply_camera(*v.position())))
