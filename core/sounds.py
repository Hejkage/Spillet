import pygame
from core.state import sound_dir
from core.settings import register_setting, get_setting

# region Sounds
pygame.mixer.init()

import time

sounds = {}
sound_categories = {}       # sound name -> its folder in assets/sounds ("abilities"...), "general" for none
default_sound_category = "general"

# VOLUME (the Sound tab in the settings menu): master x the sound's folder
register_setting("master_volume", 1.0)
register_setting("sound_volumes", {})      # folder -> 0..1. Missing = 1 (full)

def category_volume(category):
    return get_setting("sound_volumes").get(category, 1.0)

def all_sound_categories():
    """Every folder that has sounds, in alphabetical order, "general" first."""
    found = sorted(set(sound_categories.values()) - {default_sound_category})
    return [default_sound_category] + found if default_sound_category in sound_categories.values() else found

# The same sound can't start again within this many seconds.
# 10 enemies hitting on the same frame = one sound, not one 10x as loud.
sound_min_gap = 0.08
_last_played = {}

def load_sounds(dir):
    """Loads every sound in assets/sounds AND all folders inside it.
    A sound's name is its file name without .ogg/.wav/.mp3. The folder doesn't matter:
    assets/sounds/abilities/swipe_sound.ogg -> play_sound("swipe_sound")"""
    if not dir.is_dir():
        return
    for path in sorted(dir.rglob("*")):
        if path.suffix.lower() in (".wav", ".ogg", ".mp3"):
            name = path.stem
            if name in sounds:
                print(f"Two sounds are called '{name}' - using {path}")
            sounds[name] = pygame.mixer.Sound(path)
            folders = path.relative_to(dir).parts[:-1]           # assets/sounds/abilities/x.ogg -> ("abilities",)
            sound_categories[name] = folders[0] if folders else default_sound_category

# How many sounds can play at the same time (pygame's default is only 8).
sound_channels = 64
pygame.mixer.set_num_channels(sound_channels)

def play_sound(name, volume=1.0, stack=False):
    """stack=True: always plays, even if the same sound just started (drop sounds).
    stack=False: skipped if it started less than sound_min_gap ago (enemy hits)."""
    sound = sounds.get(name)
    if sound is None:
        print(f"{name} missing from sounds")
        return
    now = time.monotonic()
    if not stack and now - _last_played.get(name, -999) < sound_min_gap:
        return
    _last_played[name] = now
    volume *= get_setting("master_volume") * category_volume(sound_categories.get(name, default_sound_category))
    sound.set_volume(max(0.0, min(1.0, volume)))
    sound.play()

load_sounds(sound_dir)
