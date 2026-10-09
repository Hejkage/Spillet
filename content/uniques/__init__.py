"""One file per unique item. Every .py file in this folder is loaded automatically.

A unique is a normal base item (it goes in base_items) that:
  - builds on an existing base with "base": "twig_wand"  (sprite, slot, weapon class...)
  - always has "rarity": rarity_unique
  - has fixed lines instead of random affixes: "stats", "mods", "grants",
    "effects", "summons" - any number can be a range (low, high), rolled once
    when the item is made (see systems/bonuses.py)
  - optionally a "roll" function for random parts a range can't describe

Drop it with item_drop("its_key", weight=...) in content/drops.py.
"""
