"""KEYBINDS - every key or mouse button the game listens to has a NAME (an action).
The player can change them in the settings menu; code only ever asks by name:

    if is_action(event, "inventory"):       # in the event loop: a key / button PRESS
    if action_held("move_up"):              # every frame: is it HELD right now?
    if button_is(event.button, "basic_attack"):   # a mouse click: is this its button?

Any action can be a keyboard key OR a mouse button. Mouse buttons are stored as
negative numbers (-1 = left, -2 = middle, -3 = right, -6 / -7 = side buttons),
so the code never has to care which one it is.

A new action = one register_action() line (here, or in the file that uses it - the
hotbar registers its own skill keys). It shows up in the Keybinds tab by itself.

    register_action("map", "Open map", pygame.K_m, group="Interface")

MOVEMENT MODE (a setting): "keyboard" moves with the move_* keys, "mouse" moves
by holding move_to_mouse. Actions with mode="keyboard" / "mouse" only show up -
and only count - in that mode. A default can depend on the mode too (a function).

Escape is never bindable: it always closes things / opens the menu.
"""
import pygame
from core.settings import register_setting, get_setting, set_setting

register_setting("keybinds", {})              # action -> key / -button. Missing = its default.
register_setting("movement_mode", "keyboard") # "keyboard" or "mouse"
movement_modes = ("keyboard", "mouse")

actions = {}                                  # name -> {"label", "default", "group", "mode"}

def mouse(button):
    """A mouse button as a binding: mouse(1) = left, mouse(3) = right."""
    return -button

def movement_mode():
    mode = get_setting("movement_mode")
    return mode if mode in movement_modes else movement_modes[0]

def register_action(name, label, default, group="General", mode=None):
    """default  a pygame key (pygame.K_i), a mouse button (mouse(3)), or a function
                returning one - for a default that depends on the movement mode.
       mode     None = always. "keyboard" / "mouse" = only in that movement mode."""
    actions[name] = {"label": label, "default": default, "group": group, "mode": mode}
    return name

def set_movement_mode(mode):
    """Switch keyboard / mouse movement. If a key you set yourself now clashes
    (basic attack on left click while left click moves), it goes back to its default."""
    set_setting("movement_mode", mode)
    binds = dict(get_setting("keybinds"))
    used = {}
    for name in actions:
        if action_active(name):
            binding = key_for(name)
            if binding in used and name in binds:
                del binds[name]
            used[binding] = name
    set_setting("keybinds", binds)

def action_active(name):
    """Does this action count in the current movement mode?"""
    mode = actions[name]["mode"]
    return mode is None or mode == movement_mode()

def default_for(name):
    default = actions[name]["default"]
    return default() if callable(default) else default

def key_for(name):
    return get_setting("keybinds").get(name, default_for(name))

_mouse_names = {1: "MOUSE LEFT", 2: "MOUSE MIDDLE", 3: "MOUSE RIGHT", 6: "MOUSE 4", 7: "MOUSE 5"}
_mouse_short = {1: "LMB", 2: "MMB", 3: "RMB", 6: "M4", 7: "M5"}

def binding_label(binding, short=False):
    if not binding:
        return "-"
    if binding < 0:
        names = _mouse_short if short else _mouse_names
        return names.get(-binding, f"M{-binding}")
    return pygame.key.name(binding).upper()

def key_label(name, short=False):
    """"I", "SPACE", "MOUSE RIGHT"... for showing a key on screen. short=True: "RMB" (the hotbar)."""
    return binding_label(key_for(name), short)

def set_key(name, binding):
    """Bind `binding` to `name`. If another action (in the same mode) had it, they swap."""
    binds = dict(get_setting("keybinds"))
    old = key_for(name)
    for other in actions:
        if other != name and action_active(other) and key_for(other) == binding:
            binds[other] = old
    binds[name] = binding
    set_setting("keybinds", binds)

def reset_keys():
    set_setting("keybinds", {})

def is_action(event, name):
    if not action_active(name):
        return False
    binding = key_for(name)
    if event.type == pygame.KEYDOWN:
        return binding == event.key
    if event.type == pygame.MOUSEBUTTONDOWN:
        return binding == -event.button
    return False

def button_is(button, name):
    """Is this mouse button (event.button) the one bound to `name`?"""
    return action_active(name) and key_for(name) == -button

# pygame.mouse.get_pressed(5) order: left, middle, right, side 1, side 2
_held_index = {1: 0, 2: 1, 3: 2, 6: 3, 7: 4}

def action_held(name):
    if not action_active(name):
        return False
    binding = key_for(name)
    if not binding:
        return False
    if binding < 0:
        index = _held_index.get(-binding)
        return index is not None and pygame.mouse.get_pressed(num_buttons=5)[index]
    return pygame.key.get_pressed()[binding]

def action_groups():
    """{"Movement": [name, ...], ...} for the current movement mode, in the order registered."""
    groups = {}
    for name, a in actions.items():
        if action_active(name):
            groups.setdefault(a["group"], []).append(name)
    return groups

def _basic_attack_default():
    return mouse(3) if movement_mode() == "mouse" else mouse(1)

#               name              label                       default                group         mode
register_action("move_up",        "Move up",                  pygame.K_w,            "Movement",   mode="keyboard")
register_action("move_down",      "Move down",                pygame.K_s,            "Movement",   mode="keyboard")
register_action("move_left",      "Move left",                pygame.K_a,            "Movement",   mode="keyboard")
register_action("move_right",     "Move right",               pygame.K_d,            "Movement",   mode="keyboard")
register_action("move_to_mouse",  "Move",                     mouse(1),              "Movement",   mode="mouse")
register_action("dash",           "Dash",                     pygame.K_SPACE,        "Movement")
register_action("basic_attack",   "Basic attack",             _basic_attack_default, "Combat")
register_action("inventory",      "Inventory",                pygame.K_i,            "Interface")
register_action("equipment",      "Equipment",                pygame.K_e,            "Interface")
register_action("show_labels",    "Show all labels",          pygame.K_z,            "Interface")
register_action("debug_hitboxes", "Hitboxes",                 pygame.K_q,            "Interface")
