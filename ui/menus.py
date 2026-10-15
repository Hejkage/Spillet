import pygame
from core.state import app
from core.screen import get_font

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region menuing stuff

def draw_main_menu():
    font = get_font(108)
    title = font.render("FRESIM", True, (38, 205, 160))
    title_rect = title.get_rect(center=(app.screen_width // 2, app.screen_height // 2 - 230))
    app.screen.blit(title, title_rect)

def draw_settings_menu():
    font = get_font(72)
    text = font.render("Game Paused", True, (255, 255, 255))
    text_rect = text.get_rect(center=(app.screen_width // 2, app.screen_height // 2 - 325))
    app.screen.blit(text, text_rect)

# ---------------------------------------------------------------
# THE BARS AT THE BOTTOM: xp, health, then one bar per resource (mana...)
# Change the heights here; they stack upwards from the bottom of the screen.
# ---------------------------------------------------------------
hud_bar_width = 0.5        # part of the screen width
xp_bar_height = 12
health_bar_height = 22
resource_bar_height = 16
hud_bar_gap = 3
hud_bottom_margin = 6

def hud_bar_rect(height, from_bottom):
    """A bar `from_bottom` pixels above the bottom of the screen."""
    width = int(app.screen_width * hud_bar_width)
    return pygame.Rect(app.screen_width // 2 - width // 2, app.screen_height - from_bottom - height, width, height)

def hud_layout():
    """{"xp": rect, "health": rect, "mana": rect, ...} - resources at the bottom."""
    from systems.resources import resource_types
    rects = {}
    y = hud_bottom_margin
    for name in reversed(list(resource_types)):
        rects[name] = hud_bar_rect(resource_bar_height, y)
        y += resource_bar_height + hud_bar_gap
    rects["health"] = hud_bar_rect(health_bar_height, y)
    y += health_bar_height + hud_bar_gap
    rects["xp"] = hud_bar_rect(xp_bar_height, y)
    return rects

def draw_bar(rect, ratio, fill, back, text=None, font_size=20):
    pygame.draw.rect(app.screen, back, rect)
    pygame.draw.rect(app.screen, fill, (rect.x, rect.y, int(rect.width * max(0, min(1, ratio))), rect.height))
    pygame.draw.rect(app.screen, (255, 255, 255), rect, 2)
    if text:
        label = get_font(font_size).render(text, True, (255, 255, 255))
        app.screen.blit(label, label.get_rect(center=rect.center))

def draw_xp_bar(player):
    rect = hud_layout()["xp"]
    draw_bar(rect, player.xp / player.xp_to_next_level, (80, 180, 255), (60, 60, 60))
    level_text = get_font(20).render(f"Lvl {player.level}", True, (255, 255, 255))
    app.screen.blit(level_text, level_text.get_rect(midright=(rect.x - 10, rect.centery)))

def draw_health_bar(player):
    rect = hud_layout()["health"]
    ratio = 0 if player.max_health <= 0 else player.current_health / player.max_health
    draw_bar(rect, ratio, (200, 40, 40), (60, 0, 0), f"{int(player.current_health)} / {int(player.max_health)}", 20)
    draw_resource_bars(player)

def draw_resource_bars(player):
    """Mana, and any resource added later with register_resource()."""
    from systems.resources import resource_types, resource_max
    rects = hud_layout()
    for name, config in resource_types.items():
        maximum = resource_max(player, name)
        current = getattr(player, "resources", {}).get(name, 0)
        draw_bar(rects[name], 0 if maximum <= 0 else current / maximum, config["color"], config["back_color"],
                 f"{int(current)} / {int(maximum)}", 16)

_fps_font = None

def draw_fps(clock):
    global _fps_font
    if _fps_font is None:
        _fps_font = get_font(28)
    fps_font = _fps_font
    text = fps_font.render(f"FPS: {int(clock.get_fps())}", True, (255, 255, 0))
    app.screen.blit(text, (10, 10))
