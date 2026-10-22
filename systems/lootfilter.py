"""ITEM FILTER - which items on the ground are shown (label, hover, pick up by click).

When the filter is ON, an item is checked like this:
    0. coins: shown if the pile has at least the chosen amount (0 = every pile)
    1. it is in a group set to "Always show"  -> shown   (this always wins)
    2. it is in a group set to "Always hide"  -> hidden
    3. otherwise its RARITY decides: the chosen rarity and everything above it is shown

So "Epic and above + always show Pets" shows every epic+ item AND every pet, even common ones.

A GROUP is any kind of item you can describe. Groups are made in content/ (content/drops.py):

    register_filter_group("pets", "Pets", lambda item: getattr(item, "is_pet", False))

They show up in the Item filter tab by themselves. default= is what a new
player starts with: "normal", "show" or "hide".
"""
from core.settings import register_setting, get_setting, set_setting
from systems.rarity import all_rarities

filter_rarities = list(all_rarities)            # common ... legendary, unique - the rarity steps

register_setting("loot_filter_enabled", False)
register_setting("loot_filter_rarity", filter_rarities[0])
register_setting("loot_filter_groups", {})      # group -> "normal" / "show" / "hide"
register_setting("loot_filter_min_coins", 0)    # smallest coin pile that is shown

filter_groups = {}                              # key -> {"label", "check", "default"}
filter_modes = ("normal", "show", "hide")

def register_filter_group(key, label, check, default="normal"):
    """check(item) -> True if the item is in this group."""
    if default not in filter_modes:
        raise ValueError(f"Filter group '{key}': default must be one of {filter_modes}")
    filter_groups[key] = {"label": label, "check": check, "default": default}
    return key

def group_mode(key):
    return get_setting("loot_filter_groups").get(key, filter_groups[key]["default"])

def set_group_mode(key, mode):
    groups = dict(get_setting("loot_filter_groups"))
    groups[key] = mode
    set_setting("loot_filter_groups", groups)
    _labels_changed()

def filter_enabled():
    return get_setting("loot_filter_enabled")

def set_filter_enabled(on):
    set_setting("loot_filter_enabled", on)
    _labels_changed()

def filter_rarity():
    rarity = get_setting("loot_filter_rarity")
    return rarity if rarity in filter_rarities else filter_rarities[0]

def set_filter_rarity(rarity):
    set_setting("loot_filter_rarity", rarity)
    _labels_changed()

def min_coins():
    return int(get_setting("loot_filter_min_coins") or 0)

def set_min_coins(amount):
    set_setting("loot_filter_min_coins", max(0, int(amount)))
    _labels_changed()

def item_passes_filter(item, amount=1):
    """amount = how many are in the pile (coins on the ground stack up)."""
    if not filter_enabled():
        return True
    from systems.items import item_category_currency
    if getattr(item, "category", None) == item_category_currency:
        return amount >= min_coins()                 # coins have no rarity: only the pile size counts
    modes = {group_mode(key) for key, g in filter_groups.items() if g["check"](item)}
    if "show" in modes:
        return True
    if "hide" in modes:
        return False
    rarity = getattr(item, "rarity", None)
    if rarity not in filter_rarities:
        return True                                  # an item with no known rarity is never hidden by rarity
    return filter_rarities.index(rarity) >= filter_rarities.index(filter_rarity())

def _labels_changed():
    """Labels are laid out once; redo them so the screen matches the new filter."""
    from core.state import app
    if app.show_all_labels:
        from systems.ground import assign_label_slots
        assign_label_slots()
