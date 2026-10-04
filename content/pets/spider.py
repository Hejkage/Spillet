from systems.pets import make_pet_projectile_ability, register_pet, pet_item_key
from systems.gemtree import register_gem_node, register_gem_edge
from systems.rarity import rarity_common, rarity_uncommon, rarity_rare, rarity_epic, rarity_legendary

register_pet(
    "spider",
    name="Spider",
    name_plural="Spiders",
    sprite="spider_pet_sprite",
    item_rarity=rarity_common,          # rarity when made without one (shops). Drops roll in content/drops.py
    stats={
        # --- the ability ---
        "ability": make_pet_projectile_ability("web_shot_sprite", name="Web Shot", effects=[
            {"name": "slow", "duration": 2.0, "amount": 0.4},
        ]),
        "hit_type": "attack",          
        "damage_type": "physical",
        # "damage_split": {"nature": 60, "fire": 40},   # mixed damage instead of damage_type
        "cannot_scale": {"elemental"},                    # never gets added/increased fire
        "ability_range": 500,
        "ability_projectile_speed": 300,

        # --- shared by every rarity (rarity_overrides below replaces these) ---
        "crit_damage": 150,
    },
    # Exact numbers per rarity. Nothing here is multiplied by the rarity table.
    rarity_overrides={
        rarity_common:    {"ability_damage": 20, "crit_chance": 5,  "movement_speed": 280, "ability_cooldown": 1.2},
        rarity_uncommon:  {"ability_damage": 26, "crit_chance": 6,  "movement_speed": 300, "ability_cooldown": 1.1},
        rarity_rare:      {"ability_damage": 34, "crit_chance": 8,  "movement_speed": 320, "ability_cooldown": 1.0},
        rarity_epic:      {"ability_damage": 45, "crit_chance": 10, "movement_speed": 340, "ability_cooldown": 0.9},
        rarity_legendary: {"ability_damage": 60, "crit_chance": 12, "movement_speed": 360, "ability_cooldown": 0.8, "crit_damage": 175},
    },
)

# --- Skill tree (same system as gem trees) ---
tree = pet_item_key("spider")      # "spider_pet"
register_gem_node(tree, "start", "Spider", position=(800, 800), is_root=True)
register_gem_node(tree, "venom", "Venom", position=(800, 600),
                  stats=[{"stat": "damage", "type": "increased", "amount": 50}])
register_gem_edge(tree, "start", "venom")