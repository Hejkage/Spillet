import pygame
from core.state import app, world

# region Screen logic and display settings
app.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
app.screen_width, app.screen_height = app.screen.get_size()
base_width = app.screen_width
base_height = app.screen_height
app.ui_scale = 1.0

_font_cache = {}
def get_font(size):
    size = int(size)
    font = _font_cache.get(size)
    if font is None:
        font = pygame.font.SysFont(None, size)
        _font_cache[size] = font
    return font

#Camera
world.width = 0
world.height = 0

class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0

    def camera_update(self, target):
        self.x = int(target.x - app.screen_width // 2)
        self.y = int(target.y - app.screen_height // 2)
        self.x = max(0, min(self.x, world.width - app.screen_width))
        self.y = max(0, min(self.y, world.height - app.screen_height))

    def apply_camera(self, x, y):
        screen_x = (x - self.x)
        screen_y = (y - self.y)
        
        return screen_x, screen_y

def view_radius():
    """Half the screen's diagonal: the furthest the player can see from the centre."""
    return (app.screen_width ** 2 + app.screen_height ** 2) ** 0.5 / 2

def is_near_view(x, y, scale=1.5, pad=0):
    """True if the world point (x, y) is inside `scale` screens around the view."""
    half_w = app.screen_width * scale / 2 + pad
    half_h = app.screen_height * scale / 2 + pad
    center_x = camera.x + app.screen_width / 2
    center_y = camera.y + app.screen_height / 2
    return abs(x - center_x) <= half_w and abs(y - center_y) <= half_h

camera = Camera()
