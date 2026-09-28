# Sådan tilføjer du ting

En opslagsbog: find det du vil lave, se hvilken fil du åbner, og hvad du skriver.

---

## Grundreglen

> **Content er data. Systems er kode. Et system importerer aldrig content.**

Systems *erklærer* et registry. Content *fylder* det.

Det betyder i praksis: næsten alt hvad du tilføjer i det daglige — en ny fjende, et
nyt item, en ny gem, en ny node på et skill tree — er **ét kald i `content/`**, og
ingen andre filer skal røres.

Du skal kun ind i `systems/` når du laver en **ny mekanik der ikke findes endnu**
(fx "brændende jord efter spilleren"). Den skrives én gang, og bagefter kan alle
items bare *nævne* den i data. At skrive en mekanik per item er fejlen.

---

## Filkort

```
main.py                  loopet og intet andet

core/                    ved intet om spillets indhold
  state.py               world + app, pygame.init(), filstier
  screen.py              display, ui_scale, Camera
  assets.py              sprites, tiles, configure_sprite()
  sounds.py              lyd
  events.py              tastatur/mus-routing

systems/                 mekanik - nævner aldrig et bestemt sværd eller en slime
  items.py     rarity.py    weapons.py    status.py     supports.py
  projectiles.py drops.py   melee.py      abilities.py  world_objects.py
  ground.py    pets.py      player.py     enemies.py    areas.py
  skilltree.py gemtree.py   save.py

ui/
  widgets.py             Button, Dropdown, Checkbox
  panels.py              GridContainer, Inventory, Shop
  chest.py   hotbar.py   menus.py
  skilltree.py           det globale passive tree
  gemtree.py             per-gem trees (sockets, drag & drop)

content/                 MAPPEN DU FAKTISK REDIGERER - ren data
  gems.py                active gems, basic attacks, support gems
  items.py               affixes, weapon classes, base items, item templates
  pets/                  ÉN FIL PER PET - loades automatisk
  uniques/               ÉN FIL PER UNIQUE - loades automatisk
  enemies.py             enemy abilities og enemy definitions
  world_objects.py       træer, kister, shop-bygninger
  drops.py               drop groups og drop pools
  shops.py               shop stock og start-inventory
  areas.py               selve kortene
  skilltree.py           det globale passive tree
  gem_trees.py           per-gem trees

assets/sprites/          din kunst (assets/sprites/tiles/ til tiles)
assets/sounds/
```

Nye filer i `content/pets/` og `content/uniques/` loades af sig selv (filer der
starter med `_` springes over). Alle andre nye filer i `content/` skal tilføjes med
en `from . import <navn>` i `content/__init__.py` — **rækkefølgen betyder noget**,
hvis din fil refererer til noget fra en anden content-fil på load-tidspunktet.

---

## Sådan regnes stats

```
slutværdi = (base + flat) * (1 + increased)
```

- **base** — hvad alle starter med. Sættes i `register_stat`.
- **flat** — `"type": "flat"` mods fra items og skill tree.
- **increased** — `"type": "increased"` mods, lagt sammen og derefter ganget på én gang.

Eksempel: HP base 500, +200 flat, +10% increased → `(500 + 200) * 1.10 = 770`.

Der findes **ingen "more" multipliers** på spillerens stats. Support gems ganger
stadig på selve hittet (det er en anden pipeline), men spiller-stats er altid den
ene formel ovenfor.

### Crit

Tre stats, og de stakker:

| Stat | Gælder for |
|---|---|
| `attack_crit_chance` | kun attacks |
| `spell_crit_chance` | kun spells |
| `crit_chance` | begge — lægges oveni den relevante af de to |

Om et hit tæller som attack eller spell afgøres automatisk i `build_active_gem`
ud fra abilityens `damage_scaling`: indeholder den `spell_damage`, er det en spell,
ellers en attack. Du kan tvinge det med `"crit_type": "spell"` eller `"attack"` i
templaten.

---

# Tilføj indhold

## En ny stat

**Fil:** `systems/items.py` (undtagelse fra content-reglen — stats er selve rammen)

```python
register_stat("ward", "Ward", base=0)
```

Parametre: `base` (startværdi), `percent=True` (viser % i UI), `show_in_panel=False`
(skjul i stat-panelet — til interne stats som `physical_damage`), `panel_label=`
(andet navn i panelet end i tooltips).

Alt der læser stats kører på `stat_defs`, så stat-panelet og item-tooltips
samler den op automatisk. **Men** den gør ikke noget af sig selv — du skal selv
bruge `player.ward` et sted i koden, hvis den skal have en effekt.

---

## En ny affix (mods der rolles tilfældigt på items)

**Fil:** `content/items.py` → `affix_pool`

```python
"flat_ward": {
    "stat": "ward",
    "type": "flat",          # eller "increased"
    "weight": 5,             # valgfri, default 1 - højere = rulles oftere
    "tiers": {
        rarity_common:    (5, 10),
        rarity_uncommon:  (10, 18),
        rarity_rare:      (18, 30),
        rarity_epic:      (30, 45),
        rarity_legendary: (45, 65),
    },
},
```

Tilføj derefter nøglen (`"flat_ward"`) til `affixes`-listen på de base items der
skal kunne rulle den.

**Vigtigt:** items ruller **med replacement** — samme affix kan komme flere gange
på ét item. `weight` afgør hvor ofte den vælges, og vælges *før* tier rulles.

---

## Et nyt base item (rulles tilfældigt ved drop)

**Fil:** `content/items.py` → `base_items`

```python
"iron_helmet": {
    "name": "Iron helmet",
    "sprite": "helmet_item_sprite",
    "slot": "head",                    # SKAL matche et register_equip_slot-navn
    "affixes": ["max_health", "health_regen", "aoe", "cooldown"],
},
```

Våben tager desuden `"weapon_class": "sword"` og `"swing_sprite": "melee_attack_sprite"`.

Slot-navnene er: `ring`, `neck`, `head`, `body`, `gloves`, `belt`, `pants`,
`boots`, `weapon`, `offhand`. Skriver du `"helmet"` i stedet for `"head"`, kan
itemet ikke equippes — og der kommer ingen fejlmeddelelse.

Læg det til sidst i en drop group i `content/drops.py` med `roll_item("iron_helmet")`.

---

## Et item med faste stats (ikke tilfældigt)

**Fil:** `content/items.py` → `item_templates`

```python
"lucky_charm": {
    "kind": "equippable",
    "name": "Lucky Charm",
    "sprite": "ring_item_sprite",
    "slot": "ring",
    "stats": [
        {"stat": "attack_crit_chance", "type": "flat", "amount": 5},
        {"stat": "spell_crit_chance",  "type": "flat", "amount": 5},
    ],
    "rarity": rarity_rare,
},
```

**`stats` er en LISTE, ikke en dict.** Det er med vilje: en liste kan indeholde
den samme mod flere gange. Skriver du det som dict, overskriver ens nøgler
hinanden i stilhed, og kun den sidste overlever.

`kind` kan være: `equippable`, `active_gem`, `support_gem`, `pet`, `currency`.

Lav itemet i koden med `make_item("lucky_charm")`.

---

## Et nyt unique

**Fil:** ny fil i `content/uniques/` (kopiér `swarmcaller.py`)

```python
from systems.items import register_unique

register_unique(
    "emberheart",
    roll=roll_emberheart,            # valgfri funktion, se nedenfor
    name="Emberheart",
    sprite_name="ring_item_sprite",
    slot_type="ring",
    stats=[{"stat": "elemental_damage", "type": "increased", "amount": 25}],
)
```

Basen er fast. `roll()` returnerer en dict med de tilfældige dele, fx
`{"summon_pets": [...]}`. Hver nøgle bliver et attribut på itemet og gemmes med det.

Hver kopi lavet med `make_unique("emberheart")` rulles én gang og er derefter helt
sin egen — egne stats, egne rullede værdier, gemmes for sig. Den ændrer sig kun via
`reroll_unique(item)` (kroget til en Divine Orb-agtig currency).

Filen loades automatisk. Skal den kunne droppe, tilføj en `DropEntry` i
`content/drops.py`.

---

## En ny active gem (spell/attack)

**Fil:** `content/gems.py`

`register_active_gem` laver **tre ting på én gang**: gem-templaten, item'et der
giver den, og dens drop entry.

```python
from systems.abilities import register_active_gem, cast_projectile_spell

register_active_gem(
    "frost_lance",
    name="Frost Lance",
    function=cast_projectile_spell,
    sprite_name="frost_lance_sprite",
    weapon_tags={"caster"},                          # hvilke våben må bruge den
    support_tags={"projectile", "damage", "crit"},   # hvilke supports virker på den
    damage_scaling={"elemental_damage", "spell_damage"},
    projectile_speed=900,
    aoe=1,
    drop_weight=5,                                   # 0 = dropper aldrig, kun shop
    rarity_stats={
        rarity_common:    {"damage": 80, "cooldown": 0.9},
        rarity_uncommon:  {"damage": 110, "cooldown": 0.85},
        rarity_rare:      {"damage": 150, "cooldown": 0.8},
        rarity_epic:      {"damage": 200, "cooldown": 0.75},
        rarity_legendary: {"damage": 270, "cooldown": 0.7},
    },
)
```

Nyttige felter: `hit_kind` (`"projectile"` eller `"melee"`), `speed_stat`
(`"attack_speed"` gør cooldown til attack time), `locks_movement` + `lock_duration`,
`arc` og `swing_time` til melee, `action_group`, `action_time`, `icon`.

**Om `extra`:** felter der ikke står i `standard_gem_fields` (i `systems/abilities.py`)
ryger automatisk ned i abilityens `extra`-dict og sendes videre til dens funktion.
Sådan tilføjer du en parameter som kun din egen gem-funktion kender til.

---

## Et nyt basic attack (våbenangreb uden gem)

**Fil:** `content/gems.py`

To steder, begge i toppen af filen:

```python
basic_attack_templates.update({
    "bow_attack": {
        "name": "Bow shot",
        "function": shoot_projectile_gun,
        "sprite_name": "arrow_sprite",
        "damage_scaling": {"physical_damage"},
        "damage": 12,
        "cooldown": 0.4,
        "aoe": 0.2,
        "projectile_speed": 1000,
    },
})

basic_attacks_by_weapon_key.update({
    "bow": "bow_attack",
})
```

`basic_attacks_by_weapon` bygges automatisk af dict-comprehensionen lige under —
den skal du ikke røre. `None`-nøglen er hvad du angriber med uden våben.

---

## En ny support gem

**Fil:** `content/gems.py`

```python
register_support_gem(
    "chain", "Chaining Projectiles",
    tiers={
        rarity_common:    (1, 1),
        rarity_uncommon:  (2, 2),
        rarity_rare:      (3, 3),
        rarity_epic:      (4, 4),
        rarity_legendary: (5, 5),
    },
    apply=add_chain,                 # funktion der ændrer projectile-listen
    describe=lambda gem: f"Chains {int(gem.value)} times",
    tags=["projectile"],
    combine="add",                   # "add" eller "mul" - se nedenfor
)
```

`apply` er selve mekanikken og hører hjemme i `systems/supports.py`. Den får
`(gem, projectile_list)` og returnerer listen igen. Mønstrene findes allerede:
`scale_key("damage")` ganger et felt, `add_pierce` lægger til, `multiply_projectiles`
laver flere.

`combine` bruges kun til **visningen** af samlede mods i gem tree-panelet: `"add"`
lægger værdierne sammen (crit chance, pierce), `"mul"` ganger dem (damage, aoe —
to gems på x1.15 og x1.20 giver x1.38, ikke x2.35).

Vil du have den som drop, tilføj et `item_templates`-entry med
`{"kind": "support_gem", "gem_type": "chain", "rarity": rarity_common}` i
`content/items.py` og en `DropEntry` i `content/drops.py`.

---

## En ny weapon class

**Fil:** `content/items.py` → `weapon_class_configs`

```python
"crossbow": {"name": "Crossbow", "tags": {"ranged", "two_hand"}},
```

Tags styrer hvilke gems der må bruges med våbnet (`weapon_tags` på gemmen matches
mod disse).

---

## En ny fjende

**Fil:** `content/enemies.py` → `enemy_configs`

```python
enemy_configs.update({
    "bone_archer": {
        "base_sprite": "bone_archer_sprite",
        "health": 80,
        "xp_value": 30,
        "move_speed": 90,
        "behavior": "caster",          # melee / caster / leaper
        "attack_range": 450,
        "abilities": [witch_wand_attack],
        "drop_pool": example_drop_pool,
    },
})
```

Alt du ikke skriver, tages fra `enemy_defaults` i `systems/enemies.py` — kig der
for den fulde liste (contact_damage, cast_time, leap_*, sprite_scale osv.).

**Ny behavior** (ikke bare en ny fjende): `systems/enemies.py`

```python
def circler_behavior(e, player, dt, dx, dy, dist):
    ...
    return move_x, move_y      # eller None for "jeg har selv styr på det"

register_behavior("circler", circler_behavior)
```

Derefter er `"behavior": "circler"` nok i content.

---

## Et nyt pet

**Fil:** ny fil i `content/pets/` (kopiér `_example_pet.py`)

`register_pet` laver pet'et, pet-item'et (`<key>_pet`) og dets drop entry. Ingen
andre filer skal røres.

```python
"stats": {
    "ability": make_pet_projectile_ability("web_shot_sprite", effects=[...]),
    "ability_cooldown": 1,
    "ability_range": 500,
    "ability_projectile_speed": 300,
    "ability_damage": 25,
    "speed": 300,
},
```

**Bemærk:** pet'ets `stats` er en **dict** — det er pet'ets egen konfiguration, ikke
item-mods. Den skal *ikke* laves om til en liste. (Regel: er værdierne
`{"stat":..., "type":..., "amount":...}`-dicts, er det item-mod-systemet og skal
være en liste. Er de tal, funktioner eller configs, er det en almindelig data-dict.)

**Ny pet-bevægelse:** `register_pet_movement("dash", move, setup=None)` i
`systems/pets.py`, derefter `"movement": "dash"` i pet'ets stats.

Skal Swarmcaller kunne summone den, tilføj den til `swarmcaller_pet_weights` i
`content/uniques/swarmcaller.py`.

---

## En ny effekt (burn, slow, stun, explode...)

**Fil:** `systems/status.py`

To slags:

```python
register_status("ember_burn", ...)       # varer ved: burn, slow, stun
register_hit_effect("explode", ...)      # sker én gang: eksplosion, spawn
```

Kan kaldes fra hvilken som helst fil — også fra en enkelt pets fil.

Alt der rammer (projektiler, melee, pet-skud) bruger den bagefter ved navn:

```python
{"name": "ember_burn", "duration": 3, "dps": 4}
```

En status kan spærre for handlinger med `blocks={"attacking"}` — det er sådan
silence virker, og den stopper også contact damage.

---

## Et nyt område

**Fil:** `content/areas.py`

En `build_*`-funktion plus ét `register_area`-kald.

---

## Et nyt world object (træ, kiste, bygning)

**Fil:** `content/world_objects.py`

Felter som `blocks_movement` og `blocks_projectiles` styrer kollision.

---

## En ny drop group / drop pool

**Fil:** `content/drops.py`

```python
desert_group = [
    DropEntry(lambda: roll_item("iron_helmet"), weight=25),
    DropEntry(lambda: make_unique("emberheart"), weight=0.5),
]
```

`DropEntry(item_factory, weight=1, min_amount=1, max_amount=1)`. Grupper spredes
ind i en `DropPool` med `*desert_group`. `DropPool(entries, drop_count=(0, 2))` —
`drop_count` er hvor mange drops der rulles per død.

---

## En ny shop

**Fil:** `content/shops.py`

`register_shop(name, ShopContainer(...))` med en `ShopStock` der har
`random_entries` (vægtede) og/eller `fixed` (bestemt item i bestemt slot).

---

## En node på det globale skill tree

**Fil:** `content/skilltree.py`

```python
register_skill_node(
    "hybrid_crit", "Sharpened Instincts",
    position=(650, 400),
    stats=[{"stat": "crit_chance", "type": "increased", "amount": 15}],
)

register_skill_edge("hybrid_crit", "start")
```

- `position` er pixels på et **1600 × 1000** canvas. `(800, 500)` er midten.
  Canvas skaleres så det altid passer på skærmen. Lægger du en node uden for
  0–1600 / 0–1000, tegnes den uden for billedet og kan ikke klikkes — ingen fejl.
- `stats` bruger samme format som item-mods.
- `is_root=True` gør noden allokerbar uden naboer (indgangen til træet).
- Edges er **tovejs**: en node kan allokeres hvis *mindst én* nabo er allokeret.
  Det betyder løkker og flere veje til samme node virker helt naturligt.
- Point: **1 per level over level 1**. Max er ikke begrænset.

---

## En node på en gems eget skill tree

**Fil:** `content/gem_trees.py`

```python
register_gem_node("fireball", "burn_1", "Cinders",
                  position=(600, 500), support_type="dot_damage", value=1.20)

register_gem_node("fireball", "socket_3", "Socket",
                  position=(400, 500), is_socket=True)

register_gem_edge("fireball", "burn_1", "start")
register_gem_edge("fireball", "socket_3", "burn_1")
```

Første argument er **gem-templatens nøgle** (`"fireball"`, `"cleave"`...), så hver
gem-type har sit eget træ.

To slags noder:
- **mod-node**: `support_type` + `value`. Bruger en registreret support gem-type
  som effekt — så alle dine eksisterende supports kan bruges som tree-mods uden ny kode.
- **socket-node**: `is_socket=True`. Spilleren sætter selv en support gem i.

Regler:
- Samme canvas (**1600 × 1000**) og samme edge-logik som det globale tree.
- **Point kommer fra kills**: level 1 = 100 kills, og derefter dobbelt så mange per
  level (200, 400, 800...). Max level 10, altså max 10 point.
- Kills tælles på **alle equippede active gems**, uanset hvilken der slog ihjel.
- Hver gem-genstand har sit **eget** træ. To fireballs deler layout, men ikke point,
  kills eller sockets.
- En support gem bliver siddende i sin socket hvis du resetter træet — den gør bare
  ingenting, og du kan altid tage den ud igen.

Åbnes med **højreklik på en active gem**.

---

## En ny equipment-slot

**Fil:** `systems/items.py`

```python
register_equip_slot("gem_active6", "extra", accepts_gem(gem_slot_active), "inventory_slot_sprite")
```

Grupper: `main` (udstyr), `extra` (gems), `pet`. Lister som `active_gem_slots`
bygges automatisk ud fra registry'et lige under kaldene.

**Husk:** tilføjer du en active gem-slot, skal hotbaren også kende den —
`ui/hotbar.py` bygger `hotbar_slots` og `ability_keybinds` ud fra `active_gem_slots`,
så keybinds følger med automatisk op til tasten `9`.

---

## Et sprite der skal have en anden størrelse

**Fil:** den content-fil der bruger spritet

```python
configure_sprite("gun_basic_attack_sprite", pre_scale=4)
```

`core/assets.py` beholder kun indstillinger for UI-sprites. Andre parametre:
`scale`, `anchor`, `position`, `scale_with_screen`.

---

## En ny knap

**Fil:** `ui/widgets.py`

```python
my_button = Button("button_sprite", "Tekst", (0.02, 0.98),
                   anchor="bottom_left", action="my_action", scale=0.5)
my_button.update()
```

Position er en brøkdel af skærmen (0–1). `scale` skrumper både sprite og tekst.
Handlingen kobles på i `core/events.py` → `handle_mouse`, hvor `b.action` matches.

---

## Ny state der skal gemmes

**Fil:** `systems/save.py`

To steder, altid:

1. I `save_game()` — tilføj en nøgle til `data`-dicten.
2. I `load_game()` — læs den tilbage med `data.get("nøgle", standardværdi)`.

**Fælder:**
- JSON kan ikke gemme et `set`. Gem som `list(mit_set)`, og læs tilbage med
  `mit_set.clear()` + `mit_set.update(...)` — **ikke** `mit_set = set(...)`.
  Reassignment rammer kun navnet i `save.py`; andre filer peger stadig på det gamle
  objekt.
- Items gemmes med `item_to_dict` / `item_from_dict`. Nestede items (fx gems i
  sockets) skal selv kalde `.to_dict()` og slås op i `item_kinds` ved load.
- Ændrer du et format, så **slet `savegame.json`** før du tester. Gamle saves fejler
  sjældent højlydt — de loader bare forkert.

---

## En helt ny mekanik

Findes den ikke i forvejen (lifesteal-on-crit, brændende jord), skal den skrives
**én gang** i det relevante system. Derefter kan alle items bare nævne den i data.

At skrive mekanikken per item er fejlen — den, hele denne arkitektur er bygget for
at undgå.

---

## Fejlfinding

| Symptom | Se her |
|---|---|
| Item kan ikke equippes | `slot` i content matcher ikke et `register_equip_slot`-navn |
| Mod gør ingenting | stat-navnet findes ikke i `stat_defs` — `apply_modifier` ignorerer ukendte i stilhed |
| Kun én af flere ens mods tæller | `stats` er skrevet som dict i stedet for liste |
| Node ses ikke på et tree | `position` uden for 1600 × 1000 |
| Content loader ikke | mangler `from . import <fil>` i `content/__init__.py` |
| `NameError` efter flytning af kode | manglende `from x import y` i toppen — eller inde i funktionen, hvis modulerne kræver hinanden |
| Ability kan ikke bruges | `weapon_tags` på gemmen matcher ikke våbnets `tags` |
| Support gem gør intet | dens `tags` overlapper ikke gemmens `support_tags` |