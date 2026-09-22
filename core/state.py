import pygame
from pathlib import Path

# core.state is the first module imported, so pygame is started here.
pygame.init()
pygame.mixer.init()

# region STATE HOLDERS
# ------------------------------------------------------------------------------
# `world` holds everything that is replaced when you switch area.
# `app`   holds everything about the window / current game mode.
#
# Why holders instead of plain globals: a plain global that gets REBOUND
# (world.enemies = new_list) cannot be shared across files. `from x import enemies`
# captures the old list forever. Going through an object means the lookup happens
# at call time, so every file always sees the current value.
# ==============================================================================

class World:
    """Everything that is swapped out when the player changes area."""
    def __init__(self):
        self.current_area = None
        self.width = 0
        self.height = 0
        self.world_objects = []
        self.enemies = []
        self.ground_items = []
        self.projectiles = []
        self.enemy_projectiles = []


class App:
    """Window, display scaling, and which mode the game is in."""
    def __init__(self):
        self.screen = None
        self.screen_width = 0
        self.screen_height = 0
        self.ui_scale = 1.0
        self.fullscreen = True
        self.game_state = "menu"
        self.previous_game_state = "menu"
        self.running = True
        self.start_completed = False
        self.attack_input_blocked = False
        self.debug_hitboxes = False
        self.show_all_labels = False
        self.loot_filter_index = 0
        self.loot_filter_enabled = False
        self.label_font = None
        self.label_row_h = 0
        self.ground_label_rects = []
        self.hotbar_rects = {}


world = World()
app = App()


#File locations
base_dir = Path(__file__).resolve().parent.parent   # project root (this file lives in core/)
assets_dir = base_dir / "assets"
sprite_dir = assets_dir / "sprites"
tile_dir = sprite_dir / "tiles"
sound_dir = assets_dir / "sounds"

