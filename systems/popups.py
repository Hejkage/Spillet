import pygame
from core.state import app
from core.screen import get_font

popup_duration = 5.0
popup_rise_speed = 20   # px/sec upward drift

floating_texts = []

class FloatingText:
    def __init__(self, text, x, y, color=(255, 230, 120)):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.timer = popup_duration

    def update(self, dt):
        self.timer -= dt
        self.y -= popup_rise_speed * dt

def spawn_floating_text(text, x, y, color=(255, 230, 120)):
    floating_texts.append(FloatingText(text, x, y, color))

def update_floating_texts(dt):
    for f in floating_texts:
        f.update(dt)
    floating_texts[:] = [f for f in floating_texts if f.timer > 0]

def draw_floating_texts(camera):
    font = get_font(max(16, int(22 * app.ui_scale)))
    for f in floating_texts:
        pos = camera.apply_camera(f.x, f.y)
        surface = font.render(f.text, True, f.color)
        if f.timer < 1.0:
            surface.set_alpha(max(0, int(255 * f.timer)))
        app.screen.blit(surface, surface.get_rect(center=pos))