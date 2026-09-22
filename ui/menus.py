import pygame
from core.state import app
from core.screen import get_font

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region menuing stuff

def draw_main_menu():
    font = get_font(int(min(app.screen_width, app.screen_height) * 0.1))
    title = font.render("FRESIM", True, (255, 255, 255))
    title_rect = title.get_rect(center=(app.screen_width // 2, app.screen_height // 5))
    app.screen.blit(title, title_rect)

def draw_settings_menu():
    font = get_font(int(min(app.screen_width, app.screen_height) * 0.1))
    text = font.render("Game Paused", True, (255, 255, 255))
    text_rect = text.get_rect(center=(app.screen_width // 2, app.screen_height // 5))
    app.screen.blit(text, text_rect)

def draw_xp_bar(player):
    bar_width = int(app.screen_width * 0.5)
    bar_height = 15
    bar_x = app.screen_width // 2 - bar_width // 2
    bar_y = app.screen_height - 42

    ratio = player.xp / player.xp_to_next_level
    pygame.draw.rect(app.screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
    pygame.draw.rect(app.screen, (80, 180, 255), (bar_x, bar_y, int(bar_width * ratio), bar_height))
    pygame.draw.rect(app.screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)

    font = get_font(20)
    level_text = font.render(f"Lvl {player.level}", True, (255, 255, 255))
    app.screen.blit(level_text, (bar_x - level_text.get_width() - 10, bar_y))

def draw_health_bar(player):
    bar_width = int(app.screen_width * 0.5)
    bar_height = 25
    bar_x = app.screen_width // 2 - bar_width // 2
    bar_y = app.screen_height - 30

    ratio = 0 if player.max_health <= 0 else max(0, player.current_health / player.max_health)
    pygame.draw.rect(app.screen, (60, 0, 0), (bar_x, bar_y, bar_width, bar_height))
    pygame.draw.rect(app.screen, (200, 40, 40), (bar_x, bar_y, int(bar_width * ratio), bar_height))
    pygame.draw.rect(app.screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)

    font = get_font(22)
    hp_text = font.render(f"{int(player.current_health)} / {int(player.max_health)}", True, (255, 255, 255))
    app.screen.blit(hp_text, hp_text.get_rect(center=(bar_x + bar_width // 2, bar_y + bar_height // 2)))

_fps_font = None

def draw_fps(clock):
    global _fps_font
    if _fps_font is None:
        _fps_font = get_font(28)
    fps_font = _fps_font
    text = fps_font.render(f"FPS: {int(clock.get_fps())}", True, (255, 255, 0))
    app.screen.blit(text, (10, 10))
