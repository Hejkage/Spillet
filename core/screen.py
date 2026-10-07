import pygame
from core.state import app, world

# region Screen logic and display settings
# ---------------------------------------------------------------
# HOW THE SCREEN WORKS (like Old School RuneScape's resizable mode)
#
#   app.pixel_scale  every game pixel is shown as exactly 1x1, 2x2, 3x3... screen
#                    pixels. Always a whole number, so sprites never get uneven
#                    pixels. It only goes up when the window has room for a whole
#                    multiple of scale_step (x2 from 3840x2160, x3 from 5760x3240).
#   app.screen       what ALL game code draws on. Its size (app.screen_width /
#                    app.screen_height) is the window size / pixel_scale, so a
#                    bigger window gives more room - never bigger or blurrier things.
#   min_window       the window can't be dragged smaller than this.
#   max_view         the most of the WORLD anyone sees (game pixels). The rest of a
#                    very big or wide screen is darkened, so huge monitors don't see
#                    further than everyone else. The UI can still use the whole screen.
#
# The mouse is converted automatically: pygame.mouse.get_pos() returns GAME pixels.
# ---------------------------------------------------------------
scale_step = (1920, 1080)
min_window = (1280, 720)
max_view = (2560, 1440)
windowed_size = (1600, 900)      # size of the window when leaving fullscreen
view_limit_color = (12, 12, 12)

app.ui_scale = 1.0               # always 1: pixel_scale does the scaling now
app.pixel_scale = 1
app.display = None               # the real window. Game code never draws on it directly.

def apply_window_size():
    """Work out pixel_scale and the game screen size from the current window."""
    w, h = app.display.get_size()
    app.pixel_scale = max(1, min(w // scale_step[0], h // scale_step[1]))
    if app.pixel_scale == 1:
        app.screen = app.display                     # draw straight onto the window
    else:
        app.screen = pygame.Surface((w // app.pixel_scale, h // app.pixel_scale))
    app.screen_width, app.screen_height = app.screen.get_size()

def open_window(fullscreen):
    if fullscreen:
        app.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        app.display = pygame.display.set_mode(windowed_size, pygame.RESIZABLE)
    app.fullscreen = fullscreen
    apply_window_size()

def window_resized(width, height):
    """The window edges were dragged. Snaps back up to min_window if it got too small."""
    if width < min_window[0] or height < min_window[1]:
        app.display = pygame.display.set_mode((max(width, min_window[0]), max(height, min_window[1])), pygame.RESIZABLE)
    else:
        app.display = pygame.display.get_surface()
    apply_window_size()

def present_frame():
    """Show the finished frame. At pixel_scale 2+ the game picture is blown up by
    that whole number first. Call this instead of pygame.display.flip()."""
    if app.screen is not app.display:
        app.display.fill((0, 0, 0))                   # the 0-2 leftover pixels at the edge
        size = (app.screen_width * app.pixel_scale, app.screen_height * app.pixel_scale)
        app.display.blit(pygame.transform.scale(app.screen, size), (0, 0))
    pygame.display.flip()

def to_game_pos(pos):
    """A window position (e.g. event.pos) -> game pixels."""
    return pos[0] // app.pixel_scale, pos[1] // app.pixel_scale

_window_mouse_pos = pygame.mouse.get_pos
def mouse_pos():
    return to_game_pos(_window_mouse_pos())
pygame.mouse.get_pos = mouse_pos     # so EVERY pygame.mouse.get_pos() in the game gives game pixels

def view_rect():
    """The part of the screen where the world is visible (max_view, centred)."""
    w = min(max_view[0], app.screen_width)
    h = min(max_view[1], app.screen_height)
    return pygame.Rect((app.screen_width - w) // 2, (app.screen_height - h) // 2, w, h)

def draw_view_limit():
    """Darken the screen outside max_view. Call after the world, before the UI."""
    view = view_rect()
    if view.size == (app.screen_width, app.screen_height):
        return
    app.screen.fill(view_limit_color, (0, 0, app.screen_width, view.top))                      # top
    app.screen.fill(view_limit_color, (0, view.bottom, app.screen_width, app.screen_height))   # bottom
    app.screen.fill(view_limit_color, (0, view.top, view.left, view.height))                   # left
    app.screen.fill(view_limit_color, (view.right, view.top, app.screen_width, view.height))   # right

# ---------------------------------------------------------------
# WHERE WINDOWS (inventory, equipment, chest...) MAY GO
# hud_height keeps the bottom free for the hotbar and the health / xp bars.
# ---------------------------------------------------------------
hud_height = 126
window_margin = 10
window_gap = 10

def window_area():
    """The free part of the screen windows are placed in."""
    return pygame.Rect(window_margin, window_margin,
                       app.screen_width - window_margin * 2,
                       app.screen_height - hud_height - window_margin)

def place_centre_window(width, height, avoid=None):
    """Top-left for a window centred in window_area(). If it would overlap `avoid`
    (a Rect, e.g. the open inventory) it slides left just enough to make room."""
    area = window_area()
    x = area.centerx - width // 2
    if avoid is not None and x + width > avoid.left - window_gap:
        x = max(area.left, avoid.left - window_gap - width)
    y = max(area.top, area.centery - height // 2)
    return x, y

def place_bottom_right_window(width, height):
    """Top-left for a window pinned to the bottom-right corner of the screen."""
    return app.screen_width - window_margin - width, app.screen_height - window_margin - height

open_window(fullscreen=True)
base_width, base_height = app.screen_width, app.screen_height

_font_cache = {}
def get_font(size):
    size = int(size)
    font = _font_cache.get(size)
    if font is None:
        font = pygame.font.SysFont(None, size)
        _font_cache[size] = font
    return font

def wrap_text(text, font, max_width, indent="   "):
    """Split text into lines that fit max_width. Lines after the first are indented,
    so a wrapped row is easy to tell apart from the next row."""
    words = text.split(" ")
    lines, line = [], ""
    for word in words:
        test = f"{line} {word}" if line else word
        if font.size(test)[0] <= max_width or not line:
            line = test
        else:
            lines.append(line)
            line = indent + word
    lines.append(line)
    return lines

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
