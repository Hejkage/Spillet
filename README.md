# Project structure
Run it with `python main.py` from this folder.

## The one rule

> **Content is data. Systems are code. A system never imports content.**

Systems *declare* a registry. Content *fills* it.

```python
# systems/enemies.py          content/enemies.py
enemy_configs = {}            enemy_configs.update({
                                  "witch": {...},
                              })
```

This is what stops the circular imports, and it's why adding a 500th enemy never
touches `systems/`.

## Where things live

```
main.py                  the loop and nothing else - you rarely open this

core/                    knows nothing about your game's content
  state.py               world + app holders, pygame.init(), file paths
  screen.py              display, ui_scale, Camera
  assets.py              sprite/tile loading, scaling, sprite_rects
  sounds.py              sound loading and playback
  events.py              keyboard/mouse routing

systems/                 mechanics - never names a specific sword or slime
  rarity.py   weapons.py   status.py    supports.py   projectiles.py
  items.py    drops.py     melee.py     abilities.py  world_objects.py
  ground.py   pets.py      player.py    enemies.py    areas.py   save.py

ui/
  widgets.py             Button, Dropdown, Checkbox
  panels.py              GridContainer, Inventory, Shop
  chest.py    hotbar.py  menus.py

content/                 THE FOLDER YOU ACTUALLY EDIT - pure data
  gems.py                active gems, basic attacks, support gems
  items.py               affixes, weapon classes, base items, item templates
  pets/                  ONE FILE PER PET - loaded automatically (see _example_pet.py)
  uniques/               ONE FILE PER UNIQUE - loaded automatically (see swarmcaller.py)
  enemies.py             enemy abilities and enemy definitions
  world_objects.py       trees, chests, shop buildings
  drops.py               drop groups and drop pools
  shops.py               shop stock and starting inventory
  areas.py               the maps themselves

assets/sprites/          your art (assets/sprites/tiles/ for tiles)
assets/sounds/
```

## The state holders

The single biggest change. Globals that get **rebound** at runtime can't be shared
across files — `from x import enemies` captures the old list forever, and switching
area silently leaves half your code pointing at the previous map's enemies.

They now live on two objects: 

```python
from core.state import world, app

world.enemies          world.projectiles      world.current_area
world.ground_items     world.enemy_projectiles
world.world_objects    world.width / world.height

app.screen             app.game_state         app.ui_scale
app.screen_width       app.fullscreen         app.loot_filter_enabled
```

Attribute lookup happens at call time, so every file always sees the current value.
`switch_area()` sets `world.enemies = target.enemies` and everything follows.

Things that are assigned **once** (`player`, `equipment`, `inventory`, `chest`,
`camera`, `enemy_grid`) are still plain module globals — importing those is safe.

## Adding things

**A new enemy** — `content/enemies.py`, one dict entry:

```python
enemy_configs.update({
    "bone_archer": {
        "base_sprite": "bone_archer_sprite",
        "health": 80, "xp_value": 30, "move_speed": 90,
        "behavior": "caster", "attack_range": 450,
        "abilities": [witch_wand_attack],
        "drop_pool": example_drop_pool,
    },
})
```

**A new base item** — `content/items.py`, one entry in `base_items`.

**A new active gem** — `content/gems.py`, one call. This used to be three separate
edits (the template, the item, the drop group):

```python
from systems.abilities import register_active_gem, cast_projectile_spell

register_active_gem(
    "frost_lance",
    name="Frost Lance",
    function=cast_projectile_spell,
    sprite_name="frost_lance_sprite",
    weapon_tags={"caster"},
    support_tags={"projectile", "damage", "crit"},
    damage_scaling={"elemental_damage", "spell_damage"},
    projectile_speed=900,
    aoe=1,
    drop_weight=5,          # 0 = never drops, shop-only
    rarity_stats={
        rarity_common: {"damage": 80, "cooldown": 0.9, "crit_chance": 5},
        ...
    },
)
```

**A new pet** — one new file in `content/pets/` plus its sprite. Copy
`content/pets/_example_pet.py`, rename it, and edit it. `register_pet` creates the pet,
the pet item (`<key>_pet`) and its drop entry. No other file needs touching.
(To let Swarmcaller summon it, add it to `swarmcaller_pet_weights` in
`content/uniques/swarmcaller.py`.)

**A new effect** — `register_status(...)` (lasts a while: burn, slow, stun) or
`register_hit_effect(...)` (happens once: explode, spawn). Call it from any file, even a
single pet's file. Anything that hits (projectiles, melee, pet shots) then uses it by name:
`{"name": "ember_burn", "duration": 3, "dps": 4}`. A status can stop the target acting
with `blocks={"attacking"}` (that's how silence works now; it also stops contact damage).

**A new pet movement** — `register_pet_movement("dash", move, setup=None)`, then
`"movement": "dash"` in the pet's stats.

**A sprite that needs a different size** — `configure_sprite("name", pre_scale=2)` in the
content file that uses it. `core/assets.py` only keeps settings for UI sprites.

**A new unique** — one new file in `content/uniques/` (copy `swarmcaller.py`).
`register_unique(key, roll=fn, name=..., ...)`: the base is fixed, and `roll()` returns
the random parts, e.g. `{"summon_pets": [...]}`. Every copy made with `make_unique(key)`
(drop / shop) is rolled once and is completely separate from every other copy: it has its
own stats and rolled values, is saved on its own, and only changes through
`reroll_unique(item)` (the hook for a Divine Orb-style currency) or code that edits that
one item. Normal items work the same way: every item has its own copy of its stats.

**A new area** — `content/areas.py`: a `build_*` function plus one `register_area`.

**A new stat** — `systems/items.py`, one `register_stat` call. Everything that reads
stats works off `stat_defs`, so the stat panel and tooltips pick it up automatically.

**A new mechanic that doesn't exist yet** (lifesteal-on-crit, burning ground) — that
one *does* need code, once, in the relevant system. Every item after it just names it
in data. Writing a mechanic once is correct; writing it per-item is the failure mode.

## Notes

- `core/state.py` is imported first and runs `pygame.init()`.
- `base_dir` in `core/state.py` is the project root (`parent.parent`, since that file
  lives in `core/`). Assets resolve from there.
- A few forward references use an import **inside** the function rather than at the
  top of the file. That's deliberate and normal — it's how Python handles two modules
  that legitimately need each other at runtime but not at import time.
- The `# region` comments are preserved throughout, so search still works the way
  you're used to.
