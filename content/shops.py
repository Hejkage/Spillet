"""Shops and the player's starting inventory."""

from systems.rarity import rarity_uncommon, roll_item, roll_rarity
from systems.items import make_item
from systems.drops import DropEntry, roll_from_group
from ui.panels import Inventory, ShopContainer, ShopStock, register_shop
from .drops import active_gem_group, leather_armor_group, low_level_jewelry_group, low_level_weapons_group, support_gem_group, unique_group, wand_group

inventory = Inventory()
starting_items = [
    "support_projectiles"
]

#Shops
blacksmith = register_shop("blacksmith", ShopContainer(4, 4, reroll_cost=100, stock=ShopStock(
    fixed={
        0: roll_from_group(unique_group),                               # always a unique
        1: roll_from_group(wand_group),                                 # always a wand
        2: lambda: roll_item("leather_pants", rarity=rarity_uncommon),  # always uncommon pants
        3: lambda: make_item("bing_bong_pet")
    },
    random_entries=[
        DropEntry(lambda: roll_item("short_sword"), weight=10),
        DropEntry(lambda: make_item("fireball_gem", rarity=roll_rarity()), weight=5),
        *leather_armor_group,
        *low_level_weapons_group,
        *low_level_jewelry_group,
    ],
)))

gemsmith = register_shop("gemsmith", ShopContainer(2, 2, reroll_cost=1000, stock=ShopStock(
    fixed={},
    random_entries=[
        *active_gem_group,
        *support_gem_group,
    ],
)))

for key in starting_items:
    inventory.bags[0].add_item(make_item(key))
