import pygame
import os
from core.state import sound_dir

# region Sounds
pygame.mixer.init()

sounds = {}

def load_sounds(dir):
    if not dir.is_dir():
        return
    for file in os.listdir(dir):
        if file.endswith((".wav", ".ogg", ".mp3")):
            name = file.rsplit(".", 1)[0]
            sounds[name] = pygame.mixer.Sound(dir / file)

def play_sound(name, volume=1.0):
    sound = sounds.get(name)
    if sound is None:
        print(f"{name} missing from sounds")
        return
    sound.set_volume(volume)
    sound.play()

load_sounds(sound_dir)
