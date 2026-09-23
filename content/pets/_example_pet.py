"""TEMPLATE - not loaded (the name starts with _).

To make a new pet: copy this file, rename it (e.g. ember_fox.py), put
ember_fox_sprite.png anywhere in assets/sprites/, and change what you need.
Delete the parts you don't use - most pets only need register_pet at the bottom.

Everything below is registered by NAME, so if another pet / enemy / item later
wants "ember_burn" too, it just writes {"name": "ember_burn", ...}. You can also
move the function to a shared file then - nothing that uses it will break.
"""
from core.state import world
from core.assets import configure_sprite
from systems.status import register_status, register_hit_effect
from systems.pets import make_pet_projectile_ability, register_pet, register_pet_movement
from systems.rarity import rarity_epic

# 1. SPRITE SIZE - only needed if the folder default doesn't fit.
configure_sprite("ember_fox_sprite", pre_scale=2)


# 2. A NEW STATUS - lasts a while on the target.
#    Add blocks={"attacking"} to stop the target attacking while it has it (like silence).
def ember_burn_tick(target, status, dt):
    target.enemy_take_damage(status.get("dps", 0) * dt)

register_status("ember_burn", tick=ember_burn_tick)


# 3. A NEW HIT EFFECT - happens once, when the hit lands.
def ember_burst(target, effect, source):
    radius = effect.get("radius", 100)
    for enemy in world.enemies:
        if enemy is not target and enemy.alive:
            if (enemy.x - target.x) ** 2 + (enemy.y - target.y) ** 2 <= radius ** 2:
                enemy.enemy_take_damage(effect.get("damage", 0))

register_hit_effect("ember_burst", ember_burst)


# 4. A NEW WAY TO MOVE - dashes in short bursts instead of walking.
def dash_setup(pet):
    pet.dash_time_left = 0.0
    pet.dash_cooldown_left = 0.0

def dash_move(pet, dt, target_x, target_y, dx, dy, distance):
    pet.dash_cooldown_left -= dt
    if pet.dash_time_left <= 0 and pet.dash_cooldown_left <= 0:
        pet.dash_time_left = pet.get_stat("dash_time", 0.2)
        pet.dash_cooldown_left = pet.get_stat("dash_cooldown", 1.0)
    if pet.dash_time_left > 0:
        pet.dash_time_left -= dt
        step = min(distance, pet.get_stat("dash_speed", 900) * dt)
        pet.x += dx / distance * step
        pet.y += dy / distance * step

register_pet_movement("dash", dash_move, setup=dash_setup)


# 5. THE PET ITSELF - also creates the "ember_fox_pet" item and its drop entry.
register_pet(
    "ember_fox",
    name="Ember Fox",
    name_plural="Ember Foxes",
    sprite="ember_fox_sprite",
    item_rarity=rarity_epic,       # rarity of the pet item
    drop_weight=0.1,               # 0 = never drops (shop only)
    stats={
        "ability": make_pet_projectile_ability("fireball_sprite", effects=[
            {"name": "ember_burn", "duration": 3.0, "dps": 4},
            {"name": "ember_burst", "radius": 120, "damage": 10},
            {"name": "slow", "duration": 1.0, "amount": 0.2},   # existing effects work too
        ]),
        "ability_cooldown": 2.0,
        "ability_range": 500,
        "ability_projectile_speed": 450,
        "ability_damage": 15,
        "movement": "dash",
        "dash_speed": 900,
        "dash_time": 0.2,
        "dash_cooldown": 1.0,
    },
)
