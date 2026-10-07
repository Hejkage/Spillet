"""Flatworm - one pet that comes in a version for every damage type.

Each version is its own pet ("fire_flatworm", "frost_flatworm"...), made by the
loop at the bottom. To add a version, add one entry to flatworm_variants.
Drop chances for each version are in content/drops.py (flatworm_group).
"""
from core.state import world
from systems.status import register_status, register_hit_effect
from systems.pets import make_pet_projectile_ability, make_pet_heal_ability, register_pet, register_pet_movement, pet_item_key
from systems.gemtree import register_gem_node, register_gem_edge
from systems.rarity import rarity_common, rarity_uncommon, rarity_rare, rarity_epic, rarity_legendary


# --- 1. Effects the flatworms use (registered once, shared by every version) ---
def damage_over_time_tick(target, status, dt):
    target.enemy_take_damage(status.get("dps", 0) * dt)

register_status("ember_burn", tick=damage_over_time_tick, label="Burning", color=(255, 120, 60),
                describe=lambda e: f"Burns for {e.get('dps', 0):.0f} damage per second for {e.get('duration', 0):.1f}s")

def ember_burst(target, effect, source):
    """When the projectile HITS: every OTHER enemy within `radius` of the one it hit
    takes `damage` too. It is a real hit, so it can crit, is reduced by resistance and can burn."""
    from systems.enemies import apply_player_hit
    radius = effect.get("radius", 100)
    hit_stats = getattr(source, "hit_stats", None)
    attacker = getattr(source, "attacker", None)          # the pet, so its crit / burn chance is used
    for enemy in list(world.enemies):
        if enemy is not target and enemy.alive:
            if (enemy.x - target.x) ** 2 + (enemy.y - target.y) ** 2 <= radius ** 2:
                apply_player_hit(enemy, effect.get("damage", 0), (), hit_stats, attacker=attacker)

register_hit_effect("ember_burst", ember_burst, describe=lambda e: f"Bursts for {e.get('damage', 0):.0f} damage in a {e.get('radius', 0):.0f} radius")

# --- 2. Dash movement (shared by every version) ---
def dash_setup(pet):
    pet.dash_time_left = 0.0
    pet.dash_cooldown_left = 0.0

def dash_tick(pet, dt):
    """Every frame, also while standing still, so the cooldown never freezes."""
    pet.dash_cooldown_left -= dt
    if pet.dash_time_left > 0:
        pet.dash_time_left -= dt

def dash_move(pet, dt, target_x, target_y, dx, dy, distance):
    if pet.dash_time_left <= 0 and pet.dash_cooldown_left <= 0:
        pet.dash_time_left = pet.get_stat("dash_time", 0.2)
        pet.dash_cooldown_left = pet.get_stat("dash_cooldown", 1.0)
    if pet.dash_time_left > 0:
        step = min(distance, pet.get_stat("dash_speed", 900) * dt)
        pet.x += dx / distance * step
        pet.y += dy / distance * step
        if step >= distance:
            pet.dash_time_left = 0          # reached its spot: this dash is over

register_pet_movement("dash", dash_move, setup=dash_setup, tick=dash_tick)


# --- 3. What EVERY flatworm has. A version can override any of these in its "stats" ---
base_stats = {
    "ability_cooldown": 1.0,
    "ability_range": 500,
    "ability_projectile_speed": 450,
    "ability_damage": 15,
    "hit_type": "spell",
    "movement": "dash",
    "dash_speed": 1000,
    "dash_time": 0.2,
    "dash_cooldown": 0.5,
}


# --- 4. THE VERSIONS. Key = damage type. ---
#   name          shown in game
#   aura          "added <damage type>" it gives per rarity
#   ability       the pet's ability (a make_pet_..._ability)
#   sprite        pet sprite      (optional, default: flatworm_pet_sprite)
#   stats         overrides for base_stats above (optional)
#   per_rarity    exact stat values per rarity, e.g. heal amount (optional)
flatworm_variants = {
    "fire": {
        "name": "Fire Flatworm",
        "aura": {rarity_common: 2, rarity_uncommon: 5, rarity_rare: 8, rarity_epic: 11, rarity_legendary: 15},
        "ability": make_pet_projectile_ability("fireball_sprite", name="Ember Spit", effects=[
            {"name": "ember_burst", "radius": 120, "damage": 5},
        ]),
        "stats": {"burn_chance": 100},
    },
    "frost": {
        "name": "Frost Flatworm",
        "aura": {rarity_common: 2, rarity_uncommon: 5, rarity_rare: 8, rarity_epic: 11, rarity_legendary: 15},
        "ability": make_pet_projectile_ability("fireball_sprite", name="Frost Spit", effects=[
            {"name": "slow", "duration": 2.0, "amount": 0.4},
        ]),
    },
    "nature": {
        "name": "Nature Flatworm",
        "aura": {rarity_common: 2, rarity_uncommon: 5, rarity_rare: 8, rarity_epic: 11, rarity_legendary: 15},
        "ability": make_pet_projectile_ability("fireball_sprite", name="Venom Spit"),
        "stats": {"poison_chance": 100},
    },
    "physical": {
        "name": "Rock Flatworm",
        "aura": {rarity_common: 2, rarity_uncommon: 5, rarity_rare: 8, rarity_epic: 11, rarity_legendary: 15},
        "ability": make_pet_projectile_ability("fireball_sprite", name="Pebble Spit"),
        "stats": {"ability_damage": 25},
    },
    "shadow": {
        "name": "Shadow Flatworm",
        "aura": {rarity_common: 2, rarity_uncommon: 4, rarity_rare: 6, rarity_epic: 8, rarity_legendary: 10},
        "ability": make_pet_projectile_ability("fireball_sprite", name="Hush Spit", effects=[
            {"name": "silence", "duration": 2.0},
        ]),
    },
    "pure": {
        # Pure ignores resistance AND protection, so its numbers are lower than the rest.
        "name": "Pure Flatworm",
        "aura": {rarity_common: 1, rarity_uncommon: 2, rarity_rare: 3, rarity_epic: 4, rarity_legendary: 5},
        "ability": make_pet_heal_ability(name="Holy Light"),
        "stats": {"ability_cooldown": 8.0},
        "per_rarity": {
            rarity_common:    {"heal_amount": 10},
            rarity_uncommon:  {"heal_amount": 25},
            rarity_rare:      {"heal_amount": 50},
            rarity_epic:      {"heal_amount": 100},
            rarity_legendary: {"heal_amount": 200},
        },
    },
}

# --- 5. Build every version. You normally never need to touch this part. ---
def flatworm_rarity_overrides(damage_type, variant):
    """Per rarity: the aura buff (+ the legendary bonus) and the version's own per_rarity values."""
    overrides = {}
    for rarity, amount in variant["aura"].items():
        buffs = [{"stat": f"added_{damage_type}", "type": "flat", "amount": amount, "targets": ["player", "pets"]}]
        if rarity == rarity_legendary:
            buffs.append({"stat": "movement_speed", "type": "increased", "amount": 1, "targets": ["player"]})
        overrides[rarity] = {"buffs": buffs, **variant.get("per_rarity", {}).get(rarity, {})}
    return overrides

for damage_type, variant in flatworm_variants.items():
    key = f"{damage_type}_flatworm"                    # "fire_flatworm"
    register_pet(
        key,
        name=variant["name"],
        name_plural=variant["name"] + "s",
        sprite=variant.get("sprite", "flatworm_pet_sprite"),
        item_rarity=rarity_common,
        stats={
            **base_stats,
            "damage_type": damage_type,
            "ability": variant["ability"],
            **variant.get("stats", {}),                # the version's own overrides win
        },
        rarity_overrides=flatworm_rarity_overrides(damage_type, variant),
    )

    # Skill tree - every version gets the same start node for now
    tree = pet_item_key(key)                           # "fire_flatworm_pet"
    register_gem_node(tree, "start", variant["name"], position=(800, 800), is_root=True)