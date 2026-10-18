"""KEYBINDS - every key the game listens to has a NAME (an action). The player can
change them in the settings menu; code only ever asks by name:

    if is_action(event, "inventory"):     # in the event loop, for a key PRESS
    if action_held("move_up"):            # every frame, for a key that is HELD

A new key = one register_action() line (here, or in the file that uses it - the
hotbar registers its own skill keys). It shows up in the Keybinds tab by itself.

    register_action("map", "Open map", pygame.K_m, group="Interface")

Escape is never bindable: it always closes things / opens the menu.
"""
import pygame
from core.settings import register_setting, get_setting, set_setting

register_setting("keybinds", {})          # action -> key code. Missing = its default.

actions = {}                              # name -> {"label", "default", "group"}

def register_action(name, label, default_key, group="General"):
    actions[name] = {"label": label, "default": default_key, "group": group}
    return name

def key_for(name):
    return get_setting("keybinds").get(name, actions[name]["default"])

def key_label(name):
    """"I", "SPACE", "LEFT SHIFT"... for showing a key on screen."""
    key = key_for(name)
    return pygame.key.name(key).upper() if key else "-"

def set_key(name, key):
    """Bind `key` to `name`. If another action had that key, the two swap keys."""
    binds = dict(get_setting("keybinds"))
    old = key_for(name)
    for other in actions:
        if other != name and key_for(other) == key:
            binds[other] = old
    binds[name] = key
    set_setting("keybinds", binds)

def reset_keys():
    set_setting("keybinds", {})

def is_action(event, name):
    return event.type == pygame.KEYDOWN and event.key == key_for(name)

def action_held(name):
    key = key_for(name)
    return bool(key) and pygame.key.get_pressed()[key]

def action_groups():
    """{"Movement": [name, ...], ...} in the order they were registered."""
    groups = {}
    for name, a in actions.items():
        groups.setdefault(a["group"], []).append(name)
    return groups

#               name           label                    default key        group
register_action("move_up",     "Move up",               pygame.K_w,        "Movement")
register_action("move_down",   "Move down",             pygame.K_s,        "Movement")
register_action("move_left",   "Move left",             pygame.K_a,        "Movement")
register_action("move_right",  "Move right",            pygame.K_d,        "Movement")
register_action("dash",        "Dash",                  pygame.K_SPACE,    "Movement")
register_action("inventory",   "Inventory",             pygame.K_i,        "Interface")
register_action("equipment",   "Equipment",             pygame.K_e,        "Interface")
register_action("show_labels", "Show all item labels",  pygame.K_z,        "Interface")
register_action("debug_hitboxes", "Show hitboxes (debug)", pygame.K_q,     "Interface")
