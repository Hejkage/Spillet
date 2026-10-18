import pygame
from core.state import sound_dir

# region Sounds
pygame.mixer.init()

import time

sounds = {}

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

def play_sound(name, volume=1.0):
    sound = sounds.get(name)
    if sound is None:
        print(f"{name} missing from sounds")
        return
    now = time.monotonic()
    if now - _last_played.get(name, -999) < sound_min_gap:
        return
    _last_played[name] = now
    sound.set_volume(volume)
    sound.play()

load_sounds(sound_dir)
