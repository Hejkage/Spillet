import json, atexit
from core.state import app, base_dir
from systems.items import Item, equipment, item_kinds
from systems.player import player
from ui.widgets import loot_filter_dropdown
from ui.panels import shops
from ui.chest import chest

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Save game

def item_to_dict(item):
    return item.to_dict() if item is not None else None

def item_from_dict(data):
    if data is None:
        return None
    return item_kinds.get(data.get("kind", "generic"), Item).from_dict(data)

save_path = base_dir / "savegame.json"

def save_game():
    from content import inventory
    data = {
        "level": player.level,
        "xp": player.xp,
        "xp_to_next_level": player.xp_to_next_level,
        "coins": player.coins,
        "current_health": player.current_health,
        "equipment": {
            "main":  {s: item_to_dict(i) for s, i in equipment.main_slots.items()},
            "extra": {s: item_to_dict(i) for s, i in equipment.extra_slots.items()},
            "pets":  {s: item_to_dict(i) for s, i in equipment.pet_slots.items()},
        },
        "inventory": [item_to_dict(i) for i in inventory.bags[0].slots],
        "chest": [item_to_dict(i) for i in chest.bags[0].slots],
        "shops": {
            name: {
                "stocked": shop.stocked,
                "slots":   [item_to_dict(i) for i in shop.bags[0].slots],
                "prices":  list(shop.prices),
            }
            for name, shop in shops.items()
        },
        "settings": {
            "loot_filter_index": app.loot_filter_index,
            "loot_filter_enabled": app.loot_filter_enabled,
            "show_all_labels": app.show_all_labels,
            "start_completed": app.start_completed,
        }
    }
    with open(save_path, "w") as f:
        json.dump(data, f, indent=2)
    print("Game saved.")

def load_game():

    from content import inventory
    if not save_path.exists():
        return
    with open(save_path, "r") as f:
        data = json.load(f)

    player.level = data.get("level", 1)
    player.xp = data.get("xp", 0)
    player.xp_to_next_level = data.get("xp_to_next_level", 100)
    player.coins = data.get("coins", 0)

    equip = data.get("equipment", {})
    for slot, d in equip.get("main", {}).items():
        if slot in equipment.main_slots:
            equipment.main_slots[slot] = item_from_dict(d)
    for slot, d in equip.get("extra", {}).items():
        if slot in equipment.extra_slots:
            equipment.extra_slots[slot] = item_from_dict(d)
    for slot, d in equip.get("pets", {}).items():
        if slot in equipment.pet_slots:
            equipment.pet_slots[slot] = item_from_dict(d)

    saved_inv = data.get("inventory", [])
    bag = inventory.bags[0]
    for i in range(len(bag.slots)):
        bag.slots[i] = item_from_dict(saved_inv[i]) if i < len(saved_inv) else None
    
    saved_chest = data.get("chest", [])
    chest_bag = chest.bags[0]
    for i in range(len(chest_bag.slots)):
        chest_bag.slots[i] = item_from_dict(saved_chest[i]) if i < len(saved_chest) else None
    
    saved_shops = data.get("shops", {})
    for name, shop in shops.items():
        sdata = saved_shops.get(name)
        if sdata is None:
            continue
        bag = shop.bags[0]
        saved_slots = sdata.get("slots", [])
        for i in range(len(bag.slots)):
            bag.slots[i] = item_from_dict(saved_slots[i]) if i < len(saved_slots) else None
        saved_prices = sdata.get("prices", [])
        for i in range(len(shop.prices)):
            shop.prices[i] = saved_prices[i] if i < len(saved_prices) else 0
        shop.stocked = sdata.get("stocked", True)

    player.gem_signature = None
    player.pet_signature = None
    player.recalculate_stats()
    player.current_health = min(data.get("current_health", player.max_health), player.max_health)

    settings = data.get("settings", {})
    app.loot_filter_index = settings.get("loot_filter_index", app.loot_filter_index)
    app.loot_filter_enabled = settings.get("loot_filter_enabled", app.loot_filter_enabled)
    app.show_all_labels = settings.get("show_all_labels", app.show_all_labels)
    app.start_completed = settings.get("start_completed", app.start_completed)

    loot_filter_dropdown.selected_index = app.loot_filter_index

    print("Game loaded.")

atexit.register(lambda: save_game() if (app.game_state == "" or app.previous_game_state == "") else None)
