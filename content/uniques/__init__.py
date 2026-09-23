"""One file per unique item. Every .py file in this folder is loaded automatically.

A unique = a fixed base (name, sprite, slot...) + a roll() function for its random
parts. Each copy is rolled ONCE when it is created (drop / shop), saved with that
item, and never shared with other copies. It only changes via reroll_unique(item).
"""
