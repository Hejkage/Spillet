import pygame
import os
from core.state import app, sprite_dir, tile_dir, world
from core.screen import base_height, base_width, camera

# region Sprites
sprites = {}
tiles = {}
sprite_configs = {}
scaled_sprites = {}
sprite_rects = {}

_ui_scaled_cache = {}

def get_ui_scaled(sprite_name, width, height):
    key = (sprite_name, width, height)
    surface = _ui_scaled_cache.get(key)
    if surface is None:
        base = scaled_sprites.get(sprite_name)
        if base is None:
            return None
        surface = pygame.transform.scale(base, (width, height))
        _ui_scaled_cache[key] = surface
    return surface

# Sprite configs for UI sprites. Game sprites (characters, items, skills...)
# are set from their content file with configure_sprite() instead.
sprite_configs = {
"gear_sprite":  {
    "scale": 1,
    "anchor": "top_left",
    "position": (1, 1),
    "pre_scale": 1,
    "scale_with_screen": True
},

"button_sprite": {
    "scale": 1,
    "anchor": "center",
    "position": (0, 0),
    "pre_scale": 4,
    "scale_with_screen": True

},
}

folder_configs = {
    "characters": {
        "scale": 1,
        "anchor": "center",
        "position": (0, 0),
        "pre_scale": 1,
        "scale_with_screen": False,
    },
    "items": {
        "scale": 1,
        "anchor": "center",
        "position": (0, 0),
        "pre_scale": 1,
        "scale_with_screen": True,
    },
    "ui": {
        "scale": 1,
        "anchor": "center",
        "position": (0, 0),
        "pre_scale": 1,
        "scale_with_screen": False,
    },
    "world_objects": {
        "scale": 1,
        "anchor": "center",
        "position": (0, 0),
        "pre_scale": 1,
        "scale_with_screen": False,
    },
    "skills": {
        "scale": 1, "anchor": "center", "position": (0, 0),
        "pre_scale": 1, "scale_with_screen": False,   
    },
}

tile_configs = { 
    "grass_tile_sprite": {
        "pre_scale": 1
    },

    "stone_tile_sprite": {
        "pre_scale": 1,
    },
}

def load_sprites(dir):
    for file in os.listdir(dir):
        full = dir / file
        if full.is_file() and file.endswith(".png"):
            load_one_sprite(full, file)

    for folder_name, default_config in folder_configs.items():
        sub = dir / folder_name
        if not sub.is_dir():
            continue
        for file in os.listdir(sub):
            if not file.endswith(".png"):
                continue
            sprite_name = file.replace(".png", "")
            if sprite_name not in sprite_configs:      
                sprite_configs[sprite_name] = dict(default_config)
            load_one_sprite(sub / file, file)

sprite_paths = {}   # sprite name -> file path, so a sprite can be reloaded later

def load_one_sprite(path, file):
    sprite = pygame.image.load(path).convert_alpha()
    sprite_name = file.replace(".png", "")
    sprite_paths[sprite_name] = path

    config = sprite_configs.get(sprite_name, {})
    pre_scale = config.get("pre_scale", 1)

    if pre_scale != 1:
        sprite_width, sprite_height = sprite.get_size()
        sprite = pygame.transform.scale(sprite, (int(sprite_width * pre_scale), int(sprite_height * pre_scale)))

    sprites[sprite_name] = sprite

def load_tiles(dir): 
    for file in os.listdir(dir):
        if file.endswith(".png"):
            tile = pygame.image.load(dir / file).convert_alpha()
            tile_name = file.replace(".png", "")

            config = tile_configs.get(tile_name, {})
            pre_scale = config.get("pre_scale", 1)

            if pre_scale != 1:
                tile_width, tile_height = tile.get_size()
                tile = pygame.transform.scale(tile, (max(1, int(tile_width * pre_scale)), max(1, int(tile_height * pre_scale))))

            tiles[tile_name] = tile

load_sprites(sprite_dir)
load_tiles(tile_dir)

def update_screen_data():

    app.screen_width, app.screen_height = app.screen.get_size()

    scale_factor = min(app.screen_width / base_width, app.screen_height / base_height)
    app.ui_scale = scale_factor
    
    for sprite_name in sprites:
        scale_one_sprite(sprite_name)

    app.label_font = None

    _ui_scaled_cache.clear()

def scale_one_sprite(sprite_name):
    """Build the on-screen version of one sprite from its config."""
    sprite = sprites[sprite_name]
    scale_factor = app.ui_scale
    sprite_width, sprite_height = sprite.get_size()

    config = sprite_configs.get(sprite_name, {
        "scale": 1,
        "anchor": "center",
        "position": (None, None)   
    })

    if not config.get("scale_with_screen", True):
        local_scale = config.get("scale", 1)
        scaled_sprite = pygame.transform.scale(sprite, (int(sprite_width * local_scale), int(sprite_height * local_scale)))
        scaled_sprites[sprite_name] = scaled_sprite
        sprite_rects[sprite_name] = scaled_sprite.get_rect()
        return
    
    scaled_sprite = pygame.transform.scale(sprite, (int(sprite_width * scale_factor * config["scale"]), int(sprite_height * scale_factor * config["scale"])))
    
    scaled_sprites[sprite_name] = scaled_sprite

    sprite_rect = scaled_sprite.get_rect()
  
    if config["anchor"] == "center":
        if config["position"] != (None, None):
            sprite_rect.center = config["position"]

    elif config["anchor"] == "top_left":
        if config["position"] != (None, None):
            sprite_rect.topleft = config["position"]
    
    elif config["anchor"] == "top_right":
        if config["position"] != (None, None):
            sprite_rect.topright = config["position"]

    elif config["anchor"] == "bottom_right":
        if config["position"] != (None, None):
            sprite_rect.bottomright = config["position"]

    elif config["anchor"] == "bottom_left":
        if config["position"] != (None, None):
            sprite_rect.bottomleft = config["position"]
    
    sprite_rects[sprite_name] = sprite_rect

def configure_sprite(sprite_name, **settings):
    """Change how one sprite is sized/placed. Call it from the content file
    that uses the sprite, so you never have to edit this file:

        configure_sprite("ember_fox_sprite", pre_scale=2)

    Settings are the same keys as in folder_configs below (pre_scale, scale,
    anchor, position, scale_with_screen). Anything you leave out keeps the
    default for the sprite's folder.
    """
    if sprite_name not in sprite_paths:
        raise KeyError(f"configure_sprite: no file named '{sprite_name}.png' in assets/sprites/")
    sprite_configs[sprite_name] = {**sprite_configs.get(sprite_name, {}), **settings}
    load_one_sprite(sprite_paths[sprite_name], sprite_name + ".png")
    scale_one_sprite(sprite_name)
    for key in [k for k in _ui_scaled_cache if k[0] == sprite_name]:
        del _ui_scaled_cache[key]
        
update_screen_data()

def draw_sprite(sprite_name: str):
    config = sprite_configs.get(sprite_name)

    if sprite_name not in scaled_sprites:
        print(f"{sprite_name} missing from scaled_sprites")
        return
    
    if sprite_name not in sprite_rects:
        print(f"{sprite_name} missing from sprite_rects")
        return
    
    if config is None:
        print(f"Config missing for {sprite_name}")
        return
    
    if config.get("position") is None:
        print(f"Position missing in configs for {sprite_name}")

    app.screen.blit(scaled_sprites[sprite_name], sprite_rects[sprite_name])

def draw_background():
    tile_name = world.current_area.tile if world.current_area else "grass_tile_sprite"
    tile = tiles.get(tile_name, tiles["grass_tile_sprite"])
    tile_size = tile.get_width()

    start_x = max(0, int(camera.x // tile_size))
    start_y = max(0, int(camera.y // tile_size))

    end_x = min(world.width // tile_size + 1, start_x + app.screen_width // tile_size + 3)
    end_y = min(world.height // tile_size + 1, start_y + app.screen_height // tile_size + 3)

    for x in range(start_x, end_x):
        for y in range(start_y, end_y):

            world_x = x * tile_size
            world_y = y * tile_size

            screen_x = int(world_x - camera.x)
            screen_y = int(world_y - camera.y)
            
            app.screen.blit(tile, (screen_x, screen_y))
