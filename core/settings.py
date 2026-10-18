"""SETTINGS - everything in the settings menu, saved in settings.json next to main.py.

They are NOT part of the savegame: they belong to this computer, not to a character,
so they stay when you start a new character.

    from core.settings import register_setting, get_setting, set_setting

    register_setting("master_volume", 1.0)      # once, where the setting is used
    get_setting("master_volume")                -> 1.0
    set_setting("master_volume", 0.5)           # saved to settings.json straight away

A new setting = one register_setting() line. The settings menu (ui/settings_menu.py)
decides where it is shown.
"""
import copy
import json
from core.state import base_dir

settings_path = base_dir / "settings.json"

_defaults = {}
_values = {}

def _read_file():
    try:
        with open(settings_path, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}                              # no file yet, or a broken one: use the defaults

_from_file = _read_file()

def register_setting(key, default):
    """Make a setting exist. Its saved value (if any) is loaded right away."""
    _defaults[key] = default
    if key not in _values:
        _values[key] = copy.deepcopy(_from_file.get(key, default))
    return key

def get_setting(key):
    return _values.get(key, _defaults.get(key))

def set_setting(key, value, save=True):
    """save=False while something changes every frame (a slider being dragged);
    call save_settings() when it stops."""
    _values[key] = value
    if save:
        save_settings()

def reset_setting(key):
    set_setting(key, copy.deepcopy(_defaults.get(key)))

def save_settings():
    data = dict(_from_file)                    # keep settings nothing has registered (yet)
    data.update(_values)
    try:
        with open(settings_path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print(f"Could not save settings: {e}")
