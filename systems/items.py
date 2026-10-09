import copy
import pygame
import random
from core.state import app, world
from core.screen import camera, get_font, wrap_text, place_centre_window, window_gap
from systems.weapons import get_weapon_geometry, player_body_radius, weapon_class_tags
from systems.supports import SupportGem, roll_support_value, support_gem_types
from core.assets import get_ui_scaled, scaled_sprites, sprites, draw_window, window_size, check_window_fits
from systems.rarity import rarity_common, rarity_epic, rarity_legendary, rarity_rare, rarity_uncommon, roll_rarity, rarity_colors, rarity_order

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Items/Equipment

item_category_currency = "currency"
item_category_equipment = "equipment"
item_category_generic = "generic"

equip_slot_size = 64
equip_padding = 6

gem_slot_active = "active_gem"
gem_slot_support = "support_gem"

equip_slots = {}

def register_equip_slot(name, group, accepts, background=None, requires_grant=None):
    """requires_grant: a grant the player must have before the slot works, so a
    skill tree node can open a third ring or a fourth pet.
        requires_grant="ring_slots"         needs at least 1
        requires_grant=("ring_slots", 2)    needs at least 2 (a fourth ring)
    A locked slot is hidden while it is empty."""
    equip_slots[name] = {"group": group, "accepts": accepts, "background": background, "requires_grant": requires_grant}
    group_slots = slot_groups.setdefault(group, [])
    if name not in group_slots:
        group_slots.append(name)
    if "equipment" in globals():
        equipment.add_slot(name, group)      # registered from content/ after the equipment exists

def slots_in_group(group):
    return list(slot_groups.get(group, []))

# The slot names of each group, in order. These lists GROW when content/ registers
# a slot (ring3 in content/items.py), so always use them - never a copy.
main_equip_slots  = []
extra_equip_slots = []
pet_equip_slots   = []
slot_groups = {"main": main_equip_slots, "extra": extra_equip_slots, "pet": pet_equip_slots}

def accepts_slot_type(*types):
    """accepts_slot_type("ring") or several: accepts_slot_type("offhand", "weapon")."""
    return lambda item: getattr(item, "slot_type", None) in types

def accepts_gem(kind):
    return lambda item: getattr(item, "gem_slot", None) == kind


register_equip_slot("ring1",        "main", accepts_slot_type("ring"),      "inventory_slot_sprite")
register_equip_slot("ring2",        "main", accepts_slot_type("ring"),      "inventory_slot_sprite")
register_equip_slot("neck",         "main", accepts_slot_type("neck"),      "inventory_slot_sprite")
register_equip_slot("head",         "main", accepts_slot_type("head"),      "inventory_slot_helmet_sprite")
register_equip_slot("body",         "main", accepts_slot_type("body"),      "inventory_slot_body_sprite")
register_equip_slot("gloves",       "main", accepts_slot_type("gloves"),    "inventory_slot_sprite")
register_equip_slot("belt",         "main", accepts_slot_type("belt"),      "inventory_slot_sprite")
register_equip_slot("pants",        "main", accepts_slot_type("pants"),     "inventory_slot_pants_sprite")
register_equip_slot("boots",        "main", accepts_slot_type("boots"),     "inventory_slot_boots_sprite")
register_equip_slot("weapon",       "main", accepts_slot_type("weapon"),    "inventory_slot_sprite")
register_equip_slot("offhand",      "main", accepts_slot_type("offhand",    "weapon"), "inventory_slot_sprite")   # shields AND a second weapon

register_equip_slot("gem_active1", "extra", accepts_gem(gem_slot_active), "inventory_slot_sprite")
register_equip_slot("gem_active2", "extra", accepts_gem(gem_slot_active), "inventory_slot_sprite")
register_equip_slot("gem_active3", "extra", accepts_gem(gem_slot_active), "inventory_slot_sprite")
register_equip_slot("gem_active4", "extra", accepts_gem(gem_slot_active), "inventory_slot_sprite")
register_equip_slot("gem_active5", "extra", accepts_gem(gem_slot_active), "inventory_slot_sprite")

register_equip_slot("pet1", "pet", lambda i: getattr(i, "is_pet", False),   "inventory_slot_sprite")
register_equip_slot("pet2", "pet", lambda i: getattr(i, "is_pet", False),   "inventory_slot_sprite")
register_equip_slot("pet3", "pet", lambda i: getattr(i, "is_pet", False),   "inventory_slot_sprite")

# ---------------------------------------------------------------
# EQUIP RULES - extra rules on top of what a slot accepts.
# A rule is  fn(equipment, item, slot_name, player)  and returns None if it is
# fine, or a short reason it is not ("Two-handed weapon equipped").
# Add a rule with @equip_rule.
#
# A rule given item=None asks "is this slot usable at all right now?" - a slot
# that says no is drawn darkened (the offhand while holding a two-hander).
# Rules are ALSO checked for items already equipped (after a respec, say).
# An equipped item that breaks a rule is DISABLED: red slot, no bonuses at all.
# ---------------------------------------------------------------
equip_rules = []

def equip_rule(fn):
    equip_rules.append(fn)
    return fn

def is_two_handed(item):
    """A weapon whose weapon class has the "two_hand" tag (content/items.py)."""
    return item is not None and "two_hand" in weapon_class_tags(getattr(item, "weapon_class", None))

@equip_rule
def _two_handed_weapons(equipment, item, slot_name, player):
    """Without Titan Grip (the "dual_wield_two_handers" grant, content/skilltree.py):
    a two-handed weapon can't share your hands with an offhand item, and can't
    go in the offhand itself. One-handed weapons can always go in the offhand."""
    if player.has_grant("dual_wield_two_handers"):
        return None
    if slot_name == "offhand" and is_two_handed(equipment.main_slots.get("weapon")):
        return "Two-handed weapon equipped"
    if slot_name == "offhand" and is_two_handed(item):
        return "Two-handed weapons need both hands"
    if slot_name == "weapon" and is_two_handed(item) and equipment.main_slots.get("offhand") \
            and equipment.main_slots.get("weapon") is not item:      # only when putting it ON
        return "Remove your offhand first"
    return None

active_gem_slots = [s for s in extra_equip_slots if s.startswith("gem_active")]

stat_defs = {}

def register_stat(key, label, base=0, percent=False, show_in_panel=True, panel_label=None,
                  tab=None, always=False, cap=None, color=None, flag=False):
    """
    tab    which tab of the stats panel shows it: "defence", "offence" or "misc".
           None = not shown. (show_in_panel=True with no tab puts it on "misc".)
    always show it even at zero. Without this a zero row is hidden.
    cap    the highest value that counts. The panel shows the rest as "(x total)".
    color  the row's colour in the panel
    flag   a yes/no stat: any amount above 0 = yes. Items and the panel show
           only the label, e.g. "Immune to Poison" instead of "+1 Immune to Poison"
    """
    if tab is None and show_in_panel:
        tab = "misc"
    stat_defs[key] = {
        "label": label,
        "base": base,
        "percent": percent,
        "show_in_panel": tab is not None,
        "panel_label": panel_label or label,
        "tab": tab,
        "always": always,
        "cap": cap,
        "color": color,
        "flag": flag,
    }
    return key

register_stat("movement_speed",     "Movement Speed",                   base=350,   tab="misc", always=True)
register_stat("projectile_speed",   "Projectile Speed",                 base=100,   tab="misc", panel_label="Increased Projectile Speed")
register_stat("spell_damage",       "Spell Damage",                     base=100,   tab="offence", panel_label="Increased Spell Damage")
register_stat("attack_damage",      "Attack Damage",                    base=100,   tab="offence", panel_label="Increased Attack Damage")
register_stat("cooldown",           "Cooldown Reduction",               base=0,     tab="offence", percent=True)
register_stat("max_health",         "Health",                           base=1000,  tab="defence", always=True)
register_stat("health_regen",       "Health Regen per Second",          base=5,     tab="defence", always=True)
register_stat("lifesteal",          "Lifesteal",                        base=0,     tab="misc", percent=True)
register_stat("attack_crit_chance", "Attack Critical Strike Chance",    base=0,     tab="offence", percent=True)
register_stat("spell_crit_chance",  "Spell Critical Strike Chance",     base=0,     tab="offence", percent=True)
register_stat("crit_chance",        "Critical Strike Chance",           base=5,     tab="offence", percent=True, always=True)
register_stat("crit_damage",        "Critical Strike Damage",           base=150,   tab="offence", percent=True, always=True)
register_stat("aoe",                "Area of Effect",                   base=100,   tab="misc", panel_label="Increased Area of Effect", percent=True)
register_stat("physical_damage",    "Physical Damage",                  base=100,   tab="offence", panel_label="Increased Physical Damage")
register_stat("attack_speed",       "Attack Speed",                     base=100,   tab="offence", panel_label="Increased Attack Speed", always=True)
register_stat("attack_range",       "Attack Range",                     base=0)

# ---------------------------------------------------------------
# IMMUNITIES - gives the stat "<status>_immunity". Any amount above 0 = the
# player never gets that status. Items, the tree and pet auras give it like
# any other stat:  {"stat": "poison_immunity", "type": "flat", "amount": 1}
# One line per status you want to be able to give immunity to.
# ---------------------------------------------------------------
immunity_stats = {}          # stat -> status name

def register_immunity(status, label):
    key = register_stat(f"{status}_immunity", label, tab="defence", flag=True)
    immunity_stats[key] = status
    return key

register_immunity("poison", "Immune to Poison")
register_immunity("burn",   "Immune to Burn")

from systems.damage import (damage_colors, damage_groups, damage_keys, damage_types, flat_conditions, max_protection, max_resistance)

def register_generated_stat(key, *args, **kw):
    """For the damage stats below, which are generated from systems/damage.py.
    Your own register_stat() for the same key always wins, wherever you put it."""
    if key not in stat_defs:
        register_stat(key, *args, **kw)

for key in [*damage_types, *damage_groups]:
    name = key.replace("_", " ").title()
    shown = key in damage_types      # a group has no row: it is folded into its types
    register_generated_stat(f"{key}_resistance", f"{name} Resistance", percent=True, show_in_panel=shown,
                  tab="defence" if shown else None, cap=max_resistance, color=damage_colors.get(key))
    register_generated_stat(f"{key}_protection", f"{name} Protection", show_in_panel=shown,
                  tab="defence" if shown else None, cap=max_protection, color=damage_colors.get(key))

# Penetration. A GROUP has no row of its own: like resistance, its value is
# added into every type in it, so "2% elemental penetration" shows up as 2% on
# each element instead of as a second number to add.
for key in damage_keys:
    name = key.replace("_", " ").title()
    shown = key not in damage_groups
    register_generated_stat(f"{key}_penetration",            f"{name} Penetration",            percent=True, show_in_panel=shown, tab="offence" if shown else None, color=damage_colors.get(key))
    register_generated_stat(f"{key}_protection_penetration", f"{name} Protection Penetration", show_in_panel=shown, tab="offence" if shown else None, color=damage_colors.get(key))

# Increased damage: every type AND every group, so "increased elemental damage"
# and "increased dark damage" both exist.
for key in [*damage_types, *damage_groups]:
    name = key.replace("_", " ").title()
    register_generated_stat(f"{key}_damage", f"{name} Damage", base=100, tab="offence", panel_label=f"Increased {name} Damage", color=damage_colors.get(key))

# Flat added damage: types ONLY. A group is not a damage type, so "+30 elemental"
# would not know which resistance should reduce it.
for t in damage_types:
    name = t.replace("_", " ").title()
    register_generated_stat(f"added_{t}", f"Added {name} Damage", tab="offence", color=damage_colors.get(t))
    for condition in flat_conditions:
        register_generated_stat(f"added_{t}_{condition}", f"Added {name} Damage to {condition.replace('_', ' ').title()}s", tab="offence", color=damage_colors.get(t))

def stat_label(key):
    return stat_defs[key]["label"] if key in stat_defs else key

def stat_is_percent(key):
    return key in stat_defs and stat_defs[key]["percent"]


# ---------------------------------------------------------------
# THE STATS PANEL
# A new tab is one line here. A stat picks its tab in register_stat(tab=...).
# ---------------------------------------------------------------
stat_tabs = [("defence", "Defensive"), ("offence", "Offensive"), ("misc", "Other"), ("pets", "Pets")]

# Rows a tab shows that are not plain stats (tree mods, on-kill effects...).
# A source is fn(player) -> [(text, colour), ...]. Add one with @panel_rows("misc").
panel_extra_rows = {}

def panel_rows(tab):
    def register(fn):
        panel_extra_rows.setdefault(tab, []).append(fn)
        return fn
    return register

def _number(value):
    rounded = round(value, 2)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.2f}"

def stat_rows(player, tab):
    """Everything one tab of the stats panel shows: [(text, colour), ...]."""
    rows = []
    for stat, d in stat_defs.items():
        if d["tab"] != tab:
            continue
        value = player.stat_value(stat)
        if d["flag"]:
            if value > 0:
                rows.append((d["panel_label"], d["color"] or (255, 255, 255)))
            continue
        if d["base"] == 100:
            value -= 100                          # 130 is shown as "30% increased"
        if value == 0 and not d["always"]:
            continue
        suffix = "%" if (d["percent"] or d["base"] == 100) else ""
        text = f"{d['panel_label']}: {_number(value)}{suffix}"
        if d["cap"] is not None and value > d["cap"]:
            text = f"{d['panel_label']}: {_number(d['cap'])}{suffix}  ({_number(value)}{suffix} total)"
        rows.append((text, d["color"] or (255, 255, 255)))
    for source in panel_extra_rows.get(tab, ()):
        rows.extend(source(player))
    return rows

@panel_rows("offence")
def _rows_total_crit(player):
    """What an attack or a spell really crits with. A gem's own bonuses come on top (see its tooltip)."""
    attack, _ = player.crit_stats({"hit_type": "attack"})
    spell, _ = player.crit_stats({"hit_type": "spell"})
    return [(f"Crit chance with attacks: {attack:.1f}%", (255, 255, 255)),
            (f"Crit chance with spells: {spell:.1f}%", (255, 255, 255))]

@panel_rows("misc")
def _rows_global_mods(player):
    """Mods the skill tree and items give every ability that accepts them: pierce, extra projectiles..."""
    from systems.mods import describe_mod, mod_combine
    grouped = {}
    for name, value in getattr(player, "outside_mods", ()):
        grouped.setdefault(name, []).append(value)
    rows = []
    for name, values in grouped.items():
        if mod_combine(name) == "mul":
            total = 1.0
            for v in values:
                total *= v
        else:
            total = sum(values)
        rows.append((describe_mod(name, total), (255, 255, 255)))
    return rows

@panel_rows("misc")
def _rows_event_effects(player):
    """On-kill effects and the like, from the skill tree and items."""
    from systems.status import describe_effect, own_effect_damage
    rows = []
    for event, effects in getattr(player, "event_effects", {}).items():
        for effect in effects:
            if "damage" in effect:                     # show the damage WITH your increased stats
                damage, _ = own_effect_damage(effect, player)
                effect = dict(effect, damage=damage)
            rows.append((f"{describe_effect(effect)} ({event.replace('_', ' ')})", (255, 255, 255)))
    return rows

item_kinds = {}

class Item:
    save_kind = "generic"
    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if "save_kind" in cls.__dict__:
            item_kinds[cls.save_kind] = cls

    def __init__(self, name, sprite_name, stats=None, category=item_category_generic, rarity=rarity_common):
        self.name = name
        self.sprite_name = sprite_name
        # deepcopy: every item gets its OWN stats, never shared with its
        # template or with other copies. Changing one item never changes another.
        if isinstance(stats, dict):          
            stats = list(stats.values())
        self.stats = copy.deepcopy(stats) if stats else []
        self.category = category
        self.rarity = rarity

    def to_dict(self):
        return {"kind": self.save_kind, "name": self.name, "sprite_name": self.sprite_name, "rarity": self.rarity, "category": self.category}

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["sprite_name"], category=d.get("category", item_category_generic), rarity=d.get("rarity", rarity_common))

class EquippableItem(Item):
    """Gear. Besides stats it can carry the other bonus parts from
    systems/bonuses.py: mods, grants, effects and summons.
    base_key = the base_items key it was made from (None for item_templates)."""
    save_kind = "equippable"

    def __init__(self, name, sprite_name, slot_type, layer_sprite_name=None, stats=None, rarity=rarity_common, weapon_class=None, swing_sprite_name=None,
                 base_key=None, mods=None, grants=None, effects=None, summons=None):
        super().__init__(name, sprite_name, stats=stats, category=item_category_equipment, rarity=rarity)
        self.slot_type = slot_type
        self.layer_sprite_name = layer_sprite_name
        self.weapon_class = weapon_class
        self.swing_sprite_name = swing_sprite_name
        self.base_key = base_key
        self.mods = [tuple(m) for m in (mods or [])]
        self.grants = dict(grants or {})
        self.effects = copy.deepcopy(effects) if effects else {}
        self.summons = dict(summons or {})

    def to_dict(self):
        d = super().to_dict()
        d.update(slot_type=self.slot_type, layer_sprite_name=self.layer_sprite_name, stats=self.stats, weapon_class=self.weapon_class, swing_sprite=self.swing_sprite_name,
                 base_key=self.base_key, mods=self.mods, grants=self.grants, effects=self.effects, summons=self.summons)
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["sprite_name"], d["slot_type"], layer_sprite_name=d.get("layer_sprite_name"), stats=d.get("stats", []), rarity=d.get("rarity", rarity_common), weapon_class=d.get("weapon_class"), swing_sprite_name=d.get("swing_sprite"),
                   base_key=d.get("base_key"), mods=d.get("mods"), grants=d.get("grants"), effects=d.get("effects"), summons=d.get("summons"))

class GemItem(Item):
    def __init__(self, name, sprite_name, gem_slot, rarity=rarity_common):
        super().__init__(name, sprite_name, stats={}, category=item_category_equipment, rarity=rarity)
        self.gem_slot = gem_slot

class LevelsFromKills:
    """For items that level up from kills and have their own tree (systems/gemtree.py).
    Used by active gems AND pets, so the tree code works on both."""
    def init_tree(self, template_key):
        self.template_key = template_key      # which tree: register_gem_node(template_key, ...)
        self.kills = 0
        self.allocated = set()
        self.pending_allocated = set()
        self.sockets = {}

    def gem_level(self):
        from systems.gemtree import level_from_kills
        return level_from_kills(self.kills)

    def tree_to_dict(self, d):
        d["kills"] = self.kills
        d["allocated"] = list(self.allocated)
        d["sockets"] = {k: (v.to_dict() if v is not None else None) for k, v in self.sockets.items()}

    def tree_from_dict(self, d):
        self.kills = d.get("kills", 0)
        self.allocated = set(d.get("allocated", []))
        self.sockets = {}
        for k, sd in d.get("sockets", {}).items():
            self.sockets[k] = item_kinds[sd["kind"]].from_dict(sd) if sd else None

class ActiveGemItem(GemItem, LevelsFromKills):
    save_kind = "active_gem"

    def __init__(self, name, sprite_name, template_key, rarity=rarity_common, gem_stats=None, built_in_support=None):
        super().__init__(name, sprite_name, gem_slot_active, rarity)
        self.init_tree(template_key)
        self.gem_stats = gem_stats if gem_stats is not None else {}
        self.built_in_support = built_in_support

    def to_dict(self):
        d = super().to_dict()
        d["template_key"] = self.template_key
        d["gem_stats"] = self.gem_stats
        if self.built_in_support is not None:
            d["built_in_support"] = {
                "gem_type": self.built_in_support.gem_type,
                "value": self.built_in_support.value,
                "rarity": self.built_in_support.rarity,
            }
        self.tree_to_dict(d)
        return d

    @classmethod
    def from_dict(cls, d):
        built_in = None
        bi = d.get("built_in_support")
        if bi is not None:
            built_in = SupportGem(bi["gem_type"], bi["value"], bi["rarity"])
        item = cls(d["name"], d["sprite_name"], d["template_key"], rarity=d.get("rarity", rarity_common), gem_stats=d.get("gem_stats", {}), built_in_support=built_in)
        item.tree_from_dict(d)
        return item

class SupportGemItem(GemItem):
    save_kind = "support_gem"
    def __init__(self, gem_type, rarity=rarity_common, sprite_name="gold_coin_sprite", value=None):
        config = support_gem_types[gem_type]
        super().__init__(config["name"], sprite_name, gem_slot_support, rarity)
        self.gem_type = gem_type
        if value is None:
            value = roll_support_value(gem_type, rarity)
        self.support_gem = SupportGem(gem_type, value, rarity)

    def to_dict(self):
        d = super().to_dict()
        d.update(gem_type=self.gem_type, value=self.support_gem.value)
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(d["gem_type"], rarity=d.get("rarity", rarity_common), sprite_name=d["sprite_name"], value=d["value"])

class PetItem(Item, LevelsFromKills):
    save_kind = "pet"

    def __init__(self, name, sprite_name, pet_type, rarity=rarity_common):
        from systems.pets import pet_item_key
        super().__init__(name, sprite_name, category=item_category_generic, rarity=rarity)
        self.pet_type = pet_type
        self.is_pet = True
        self.init_tree(pet_item_key(pet_type))     # "spider" -> tree "spider_pet"

    def to_dict(self):
        d = super().to_dict()
        d["pet_type"] = self.pet_type
        self.tree_to_dict(d)
        return d

    @classmethod
    def from_dict(cls, d):
        item = cls(d["name"], d["sprite_name"], d["pet_type"], rarity=d.get("rarity", rarity_common))
        item.tree_from_dict(d)
        return item

# ---------------------------------------------------------------
# EQUIPMENT PANEL LAYOUT
# Where each MAIN slot sits on the paper doll: (column, row) on a grid.
# The middle (equip_model_area) is kept empty for the player model.
# Move a slot = change its numbers. New slot = register_equip_slot() + one line here.
#
#   col:  0        1     2      3     4
#   row0  neck     .     head   ring3 ring1      (ring3 only shows once unlocked)
#   row1  body     [            ]     ring2
#   row2  belt     [   model    ]     gloves
#   row3  pants    [            ]     .
#   row4  weapon   .     boots  .     offhand
# ---------------------------------------------------------------
equip_doll_columns = 5
equip_doll_rows = 5
equip_doll_layout = {
    "neck":   (0, 0),                     "head": (2, 0),       "ring3": (3, 0),  "ring1":  (4, 0),
    "body":   (0, 1),                                                             "ring2":  (4, 1),
    "belt":   (0, 2),                                                             "gloves": (4, 2),
    "pants":  (0, 3),                                                             "boots":  (4, 3),
                       "weapon": (1, 4),                    "offhand": (3, 4),
}
equip_model_area = ((1, 1), (3, 3))     # (top-left cell, bottom-right cell) kept empty

blocked_slot_color  = (0, 0, 0, 150)       # empty slot you can't use right now
disabled_slot_color = (200, 30, 30, 140)    # item equipped but disabled (red)

class Equipment:
    def __init__(self):
        self.main_slots = {slot: None for slot in main_equip_slots}
        self.extra_slots = {slot: None for slot in extra_equip_slots}
        self.pet_slots = {slot: None for slot in pet_equip_slots}
        self.open = False
        self.drag_source = None
        self.rect = None
        self.stat_tab = stat_tabs[0][0]     # which tab of the stats panel is showing
        self.stat_tab_rects = {}
        self.stat_rect = None
        self.stat_scroll = 0

    def toggle(self):
        self.open = not self.open

    def add_slot(self, name, group):
        """A slot registered after the equipment was made (from content/)."""
        slots = {"main": self.main_slots, "extra": self.extra_slots, "pet": self.pet_slots}[group]
        slots.setdefault(name, None)
    
    def equip_problem(self, item, slot_name):
        """None if `item` may go in `slot_name`, else the reason it may not.
        item=None asks whether the slot is usable at all right now."""
        from systems.player import player      # late: player.py imports this file
        d = equip_slots.get(slot_name)
        if not d:
            return "No such slot"
        if item is not None and not d["accepts"](item):
            return "Doesn't fit here"
        if not self.slot_unlocked(slot_name):
            return "Slot locked"
        for rule in equip_rules:
            reason = rule(self, item, slot_name, player)
            if reason:
                return reason
        return None

    def can_equip(self, item, slot_name):
        return self.equip_problem(item, slot_name) is None

    def slot_unlocked(self, slot_name):
        """False while the slot's requires_grant is missing (e.g. no third ring yet)."""
        from systems.player import player
        needed = equip_slots.get(slot_name, {}).get("requires_grant")
        if not needed:
            return True
        name, amount = needed if isinstance(needed, tuple) else (needed, 1)
        return player.grant_value(name) >= amount

    def item_in(self, slot_name):
        for slots in (self.main_slots, self.extra_slots, self.pet_slots):
            if slot_name in slots:
                return slots[slot_name]
        return None

    def is_disabled(self, slot_name):
        """True if the item IN this slot breaks a rule right now - e.g. the offhand
        after a respec took away Titan Grip. It stays equipped but does nothing."""
        item = self.item_in(slot_name)
        return item is not None and self.equip_problem(item, slot_name) is not None

    def working_items(self):
        """Equipped gear and gems that count: [(slot_name, item), ...]. Disabled ones are left out."""
        return [(slot, item) for slots in (self.main_slots, self.extra_slots)
                for slot, item in slots.items() if item is not None and not self.is_disabled(slot)]
    
    def draw(self, scaled_sprites, player):
        if not self.open:
            return

        scale = app.ui_scale
        slot_size = max(1, int(equip_slot_size * scale))
        padding = max(1, int(equip_padding * scale))
        margin = max(1, int(20 * scale))
        cell = slot_size + padding                         # one grid step: a slot plus the gap after it
        header_font = get_font(max(12, int(18 * scale)))
        header_h = header_font.get_height() + padding

        # the rows under the paper doll: (title, slot names, where the items live, where the rects go)
        self.pet_slots_rects = {}
        self.extra_slots_rects = {}
        bottom_rows = [
            ("Pets",       pet_equip_slots,   self.pet_slots,   self.pet_slots_rects),
            ("Skill Gems", extra_equip_slots, self.extra_slots, self.extra_slots_rects),
        ]

        doll_w = equip_doll_columns * cell - padding
        doll_h = equip_doll_rows * cell - padding
        widest_row = max(len(slots) for _, slots, _, _ in bottom_rows) * cell - padding
        check_window_fits("equipment", margin * 2 + max(doll_w, widest_row),
                          margin * 2 + doll_h + len(bottom_rows) * (padding * 2 + header_h + slot_size))

        # stats + equipment are placed as ONE block: centred, sliding left if the inventory is in the way.
        # Their sizes come from register_window() in core/assets.py.
        from content import inventory
        stats_width, stats_height = window_size("stats")
        panel_width, panel_height = window_size("equipment")
        avoid = inventory.planned_rect() if inventory.open else None
        stats_x, panel_y = place_centre_window(stats_width + window_gap + panel_width,
                                               max(stats_height, panel_height), avoid)
        panel_x = stats_x + stats_width + window_gap
        self.rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        draw_window("equipment", self.rect)

        self.draw_stat_panel(scaled_sprites, player, stats_x, panel_y, scale)

        # --- the paper doll: main slots around an empty middle ---
        doll_x = panel_x + (panel_width - doll_w) // 2
        doll_y = panel_y + margin

        (c0, r0), (c1, r1) = equip_model_area
        self.model_rect = pygame.Rect(doll_x + c0 * cell, doll_y + r0 * cell,
                                      (c1 - c0 + 1) * cell - padding, (r1 - r0 + 1) * cell - padding)
        shade = pygame.Surface(self.model_rect.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 35))                          # placeholder until the player model is drawn here
        app.screen.blit(shade, self.model_rect)

        self.main_slot_rects = {}
        for slot in main_equip_slots:
            if slot not in equip_doll_layout:
                continue                                   # not placed yet: add it to equip_doll_layout
            if self.main_slots[slot] is None and not self.slot_unlocked(slot):
                continue                                   # locked and empty: hidden until a grant opens it
            col, row = equip_doll_layout[slot]
            rect = pygame.Rect(doll_x + col * cell, doll_y + row * cell, slot_size, slot_size)
            self.main_slot_rects[slot] = rect
            self.draw_slot(scaled_sprites, rect, self.main_slots[slot], slot)

        # --- pets and gems: one centred row each, with a small title ---
        y = doll_y + doll_h + padding * 2
        for title, slots, contents, rects in bottom_rows:
            text = header_font.render(title, True, (230, 230, 230))
            app.screen.blit(text, text.get_rect(midtop=(panel_x + panel_width // 2, y)))
            y += header_h
            row_x = panel_x + (panel_width - (len(slots) * cell - padding)) // 2
            for i, slot in enumerate(slots):
                rect = pygame.Rect(row_x + i * cell, y, slot_size, slot_size)
                rects[slot] = rect
                self.draw_slot(scaled_sprites, rect, contents[slot], slot)
            y += slot_size + padding * 2

    def draw_slot(self, scaled_sprites, rect, item, slot_name=None):
        bg_name = equip_slots.get(slot_name, {}).get("background") or "inventory_slot_sprite"
        slot_sprite = scaled_sprites.get(bg_name) or scaled_sprites.get("inventory_slot_sprite")
        if slot_sprite:
            scaled_slot = pygame.transform.scale(slot_sprite, (rect.width, rect.height))
            app.screen.blit(scaled_slot, rect)

        if slot_name and item is not None and self.is_disabled(slot_name):
            shade = pygame.Surface(rect.size, pygame.SRCALPHA)
            shade.fill(disabled_slot_color)                # equipped but breaking a rule: does nothing
            app.screen.blit(shade, rect)
        elif slot_name and item is None and self.equip_problem(None, slot_name):
            shade = pygame.Surface(rect.size, pygame.SRCALPHA)
            shade.fill(blocked_slot_color)                 # unusable right now, e.g. offhand with a two-hander
            app.screen.blit(shade, rect)

        if item:
            item_sprite = scaled_sprites.get(item.sprite_name)
            if item_sprite:
                fitted = scale_item_sprite(item_sprite, rect.width * 0.9)
                app.screen.blit(fitted, fitted.get_rect(center=rect.center))

        try_set_hover(item, rect)

    def draw_stat_panel(self, scaled_sprites, player, stats_x, panel_y, scale):
        panel_width, panel_height = window_size("stats")     # register_window("stats", ...) in core/assets.py
        self.stat_rect = pygame.Rect(stats_x, panel_y, panel_width, panel_height)
        draw_window("stats", self.stat_rect)

        pad = int(20 * scale)
        text_x = stats_x + pad

        level_font = get_font(max(20, int(34 * scale)))  # bigger than the normal stat font
        label_surf = level_font.render("Level: ", True, (200, 200, 200))
        value_surf = level_font.render(str(player.level), True, (255, 255, 255))
        app.screen.blit(label_surf, (text_x, panel_y + pad))
        app.screen.blit(value_surf, (text_x + label_surf.get_width(), panel_y + pad))
        y = panel_y + pad + level_font.get_height() + int(8 * scale)

        # tabs
        tab_font = get_font(max(14, int(20 * scale)))
        gap = int(6 * scale)
        tab_w = (panel_width - pad * 2 - gap * (len(stat_tabs) - 1)) // len(stat_tabs)
        tab_h = tab_font.get_height() + int(8 * scale)
        self.stat_tab_rects = {}
        for i, (tab, label) in enumerate(stat_tabs):
            rect = pygame.Rect(text_x + i * (tab_w + gap), y, tab_w, tab_h)
            self.stat_tab_rects[tab] = rect
            active = tab == self.stat_tab
            pygame.draw.rect(app.screen, (95, 75, 35) if active else (40, 40, 40), rect, border_radius=4)
            pygame.draw.rect(app.screen, (240, 200, 60) if active else (90, 90, 90), rect, width=1, border_radius=4)
            text = tab_font.render(label, True, (255, 255, 255) if active else (170, 170, 170))
            app.screen.blit(text, text.get_rect(center=rect.center))
        y += tab_h + int(10 * scale)

        # the rows of the open tab, scrolled with the mouse wheel
        font = get_font(max(13, int(21 * scale)))
        row_h = font.get_linesize()
        view = pygame.Rect(stats_x, y, panel_width, panel_y + panel_height - y - pad)
        rows = []
        for text, color in stat_rows(player, self.stat_tab):          # long rows wrap instead of going off the panel
            rows.extend((line, color) for line in wrap_text(text, font, panel_width - pad * 2))
        self.stat_scroll = max(0, min(self.stat_scroll, len(rows) * row_h - view.height))

        app.screen.set_clip(view)
        for i, (text, color) in enumerate(rows):
            row_y = view.y + i * row_h - self.stat_scroll
            if row_y + row_h < view.y or row_y > view.bottom:
                continue
            app.screen.blit(font.render(text, True, color), (text_x, row_y))
        app.screen.set_clip(None)

    def scroll_stats(self, wheel):
        """Mouse wheel over the stats panel scrolls the open tab."""
        if self.open and self.stat_rect and self.stat_rect.collidepoint(pygame.mouse.get_pos()):
            self.stat_scroll = max(0, self.stat_scroll - wheel * 40)
                            
    def handle_click(self, pos, button, drag_state, player):
        if not self.open or button != 1:
            return False
        
        for tab, rect in self.stat_tab_rects.items():
            if rect.collidepoint(pos):
                self.stat_tab = tab
                self.stat_scroll = 0
                return True
        if self.stat_rect and self.stat_rect.collidepoint(pos):
            return True      # a click on the stats panel is not an attack
        
        all_slots = {}
        if hasattr(self, "main_slot_rects"):
            all_slots = {**self.main_slot_rects, **self.extra_slots_rects, **self.pet_slots_rects}

        for slot_name, rect in all_slots.items():
            if rect.collidepoint(pos):
                if slot_name in self.main_slots:
                    slot_dict = self.main_slots
                elif slot_name in self.extra_slots:
                    slot_dict = self.extra_slots
                else:
                    slot_dict = self.pet_slots
                
                if drag_state.item is None:
                    if slot_dict[slot_name] is not None:
                        drag_state.item = slot_dict[slot_name]
                        slot_dict[slot_name] = None
                        drag_state.source = ("equipment", slot_name)
                else:
                    if self.can_equip(drag_state.item, slot_name):
                        existing = slot_dict[slot_name]
                        slot_dict[slot_name] = drag_state.item
                        drag_state.item = existing
                        drag_state.source = ("equipment", slot_name) if existing else None
                return True
            
        if self.rect and self.rect.collidepoint(pos):
            return True
        
        return False

class DragState:
    def __init__(self):
        self.item = None
        self.source = None

def scale_item_sprite(item_sprite, box_size):
    box = max(1, int(box_size))
    iw, ih = item_sprite.get_size()
    fit = min(box / iw, box / ih)
    return pygame.transform.scale(item_sprite, (max(1, int(iw * fit)), max(1, int(ih * fit))))

def draw_dragged_item():
    if drag_state.item:
        item_sprite = scaled_sprites.get(drag_state.item.sprite_name)
        if item_sprite:
            scale = app.ui_scale
            slot_size = max(1, int(equip_slot_size * scale))
            fitted = scale_item_sprite(item_sprite, slot_size * 0.9)
            mouse_pos = pygame.mouse.get_pos()
            app.screen.blit(fitted, fitted.get_rect(center=mouse_pos))

tooltip_sections = []

def tooltip_section(fn):
    tooltip_sections.append(fn)
    return fn

_WHITE = (255, 255, 255)
_GRAY  = (200, 200, 200)

def _format_mod_line(mod):
    stat = mod.get("stat")
    label = stat_label(stat)
    amount = mod.get("amount", 0)
    mod_type = mod.get("type")
    if stat in stat_defs and stat_defs[stat]["flag"]:
        return label                                   # "Immune to Poison"
    if mod_type == "flat":
        suffix = "%" if stat_is_percent(stat) else ""
        return f"{amount:+g}{suffix} {label}"                     # +20 / -20
    elif mod_type == "increased":
        if amount < 0:
            return f"{-int(amount)}% reduced {label}"             # -10 -> "10% reduced"
        return f"+{int(amount)}% increased {label}"

@tooltip_section
def _tt_two_handed(item, lines):
    if is_two_handed(item):
        lines.append(("Two-handed weapon", _GRAY))

@tooltip_section
def _tt_stats(item, lines):
    if pygame.key.get_mods() & pygame.KMOD_ALT:
        for mod in item.stats:
            color = rarity_colors.get(mod.get("tier"), _WHITE)
            lines.append((_format_mod_line(mod), color))
        return

    grouped = {}
    for mod in item.stats:
        key = (mod.get("stat"), mod.get("type"))
        g = grouped.setdefault(key, {"amount": 0, "count": 0, "tier": mod.get("tier")})
        g["amount"] += mod.get("amount", 0)
        g["count"] += 1
        if rarity_order.index(mod.get("tier", rarity_common)) > rarity_order.index(g["tier"] or rarity_common):
            g["tier"] = mod.get("tier")

    for (stat, mod_type), g in grouped.items():
        color = rarity_colors.get(g["tier"], _WHITE)
        text = _format_mod_line({"stat": stat, "type": mod_type, "amount": g["amount"]})
        if g["count"] > 1:
            text = f"({g['count']}) {text}"
        lines.append((text, color))

@tooltip_section
def _tt_attack_range(item, lines):
    if "melee" not in weapon_class_tags(getattr(item, "weapon_class", None)):
        return
    swing_name = getattr(item, "swing_sprite_name", None)
    if swing_name not in sprites:
        return
    geom = get_weapon_geometry(swing_name)
    lines.append((f"{player_body_radius + geom['reach']:.0f} Base attack range", _GRAY))

@tooltip_section
def _tt_bonuses(item, lines):
    """Mods, grants, effects and summons (the stats are shown above)."""
    if isinstance(item, EquippableItem):
        from systems.bonuses import describe_bonuses
        for text in describe_bonuses(item, include_stats=False):
            lines.append((text, _WHITE))

@tooltip_section
def _tt_support_gem(item, lines):
    if hasattr(item, "support_gem"):
        lines.append((item.support_gem.describe(), _WHITE))

@tooltip_section
def _tt_gem_level(item, lines):
    if not hasattr(item, "template_key"):
        return
    from systems.gemtree import max_gem_level, kills_into_current_level, kills_needed_for_next
    level = item.gem_level()
    if level < max_gem_level:
        lines.append((f"Level {level}/{max_gem_level}  ({kills_into_current_level(item)}/{kills_needed_for_next(item)} kills)", _GRAY))
    else:
        lines.append((f"Level {level}/{max_gem_level} (max)", _GRAY))

@tooltip_section
def _tt_active_gem(item, lines):
    """An active gem item: its OWN base numbers, before the player's stats.
    What it does once equipped is the hotbar tooltip; what the tree adds is the tree."""
    from systems.abilities import active_gem_templates, template_speed_stat, template_uses_aoe
    from systems.damage import damage_colors, damage_split
    if not hasattr(item, "template_key") or item.template_key not in active_gem_templates:
        return
    t = active_gem_templates[item.template_key]
    rolled = getattr(item, "gem_stats", {})

    def gem_val(stat, default=None):
        return rolled.get(stat, t.get(stat, default))

    damage = gem_val("damage")
    if damage is not None:
        from systems.damage import damage_lines
        lines.extend(damage_lines({k: damage * share for k, share in damage_split(t).items()}))

    projectiles = gem_val("projectiles")
    if projectiles and projectiles > 1:
        lines.append((f"{int(projectiles)} projectiles", _WHITE))

    cooldown = gem_val("attack_time")
    if cooldown is None:
        cooldown = gem_val("cooldown")
    if cooldown is not None:
        lines.append((f"{cooldown:.2f}s {'base attack time' if template_speed_stat(t) else 'base cooldown'}", _WHITE))

    cast_time = t.get("action_time", t.get("swing_time"))
    if cast_time:
        lines.append((f"{cast_time:.2f}s cast time", _WHITE))

    cc = gem_val("crit_chance", 0)
    if cc:
        lines.append((f"{cc:.0f}% crit chance", _WHITE))
    cdmg = gem_val("crit_damage", 0)
    if cdmg:
        lines.append((f"+{cdmg:.0f}% crit damage", _WHITE))

    from systems.ailments import ailment_stats, ailment_text
    for key, label, base, percent, text in ailment_stats:          # e.g. "Chance to burn: 5%"
        value = gem_val(key, 0)
        if value:
            lines.append((ailment_text(text, value), _WHITE))

    dot_damage = gem_val("dot_damage", 0)
    if dot_damage:
        lines.append((f"{dot_damage:.0f} damage per second", _WHITE))
        dot_duration = gem_val("dot_duration", 0)
        if dot_duration:
            lines.append((f"{dot_duration:.0f}s damage over time", _WHITE))

    speed = gem_val("projectile_speed")
    if speed:
        lines.append((f"{speed:.0f} projectile speed", _WHITE))

    gem_aoe = gem_val("aoe")
    if gem_aoe is not None and template_uses_aoe(t):
        lines.append((f"{gem_aoe * 100:.0f}% area of effect", _WHITE))

    blocked = t.get("blocked")
    if blocked:
        lines.append((f"Can't scale with: {', '.join(sorted(blocked))}", _GRAY))

    built_in = getattr(item, "built_in_support", None)
    if built_in is not None:
        lines.append((f"Built-in: {built_in.describe()}", rarity_colors.get(built_in.rarity, _WHITE)))

def draw_tooltip_box(lines):
    font = get_font(max(16, int(20 * app.ui_scale)))
    rendered = [font.render(text, True, color) for text, color in lines]

    padding = 10
    width = max(t.get_width() for t in rendered) + padding * 2
    height = sum(t.get_height() for t in rendered) + padding * 2

    mouse_x, mouse_y = pygame.mouse.get_pos()
    box_x = mouse_x + 20
    box_y = mouse_y

    if box_x + width > app.screen_width:
        box_x = mouse_x - width - 20
    box_x = max(0, min(box_x, app.screen_width - width))
    box_y = max(0, min(box_y, app.screen_height - height))

    box_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    box_surface.fill((20, 20, 20, 230))
    app.screen.blit(box_surface, (box_x, box_y))

    y_offset = box_y + padding
    for t in rendered:
        app.screen.blit(t, (box_x + padding, y_offset))
        y_offset += t.get_height()

def draw_item_tooltip():
    item = hover_state.item
    if not item:
        return
    name_color = rarity_colors.get(item.rarity, _WHITE)
    lines = [(item.name, name_color)]
    for section in tooltip_sections:
        section(item, lines)
    draw_tooltip_box(lines)

def draw_ground_item_label():
    from systems.ground import ground_label_color, ground_label_text
    g = hover_state.ground_item
    if not g:
        return

    scale = app.ui_scale
    font_size = max(16, int(22 * scale))
    font = get_font(font_size)

    color = ground_label_color(g)
    text = font.render(ground_label_text(g), True, color)

    padding = 8
    width = text.get_width() + padding * 2
    height = text.get_height() + padding * 2

    mouse_x, mouse_y = pygame.mouse.get_pos()
    box_x = mouse_x + 20
    box_y = mouse_y - height - 5

    box_x = max(0, min(box_x, app.screen_width - width))
    box_y = max(0, min(box_y, app.screen_height - height))

    box_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    box_surface.fill((20, 20, 20, 230))
    app.screen.blit(box_surface, (box_x, box_y))
    app.screen.blit(text, (box_x + padding, box_y + padding))

def draw_all_ground_labels():
    from systems.ground import get_label_font, ground_label_color, ground_label_text, item_passes_filter, label_box_width
    app.ground_label_rects = []

    if not app.show_all_labels:
        return

    font = get_label_font()
    h = app.label_row_h

    for g in world.ground_items:
        if not item_passes_filter(g.item):        
            continue
        if g.label_offset is None or g.label_anchor is None:
            continue

        off_x, off_y = g.label_offset
        ax, ay = g.label_anchor
        w = label_box_width(g)                     

        cx, cy = camera.apply_camera(ax + off_x, ay + off_y)
        rect = pygame.Rect(0, 0, w, h)
        rect.centerx = int(cx)      
        rect.top = int(cy)

        if rect.right < 0 or rect.left > app.screen_width or rect.bottom < 0 or rect.top > app.screen_height:
            continue

        color = ground_label_color(g)              
        text = font.render(ground_label_text(g), True, color)  

        box = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        box.fill((20, 20, 20, 255))
        app.screen.blit(box, rect)

        has_built_in = getattr(g.item, "built_in_support", None) is not None
        text_rect = text.get_rect(center=rect.center)

        if has_built_in:
            icon = scaled_sprites.get("star_icon_sprite")
            if icon:
                icon_size = text.get_height()
                fitted = scale_item_sprite(icon, icon_size)
                text_rect.centerx += (icon_size + 2) // 2
                icon_rect = fitted.get_rect(midright=(text_rect.left - 2, rect.centery))
                app.screen.blit(fitted, icon_rect)

        app.screen.blit(text, text_rect)
        app.ground_label_rects.append((rect, g))

class HoverState:
    def __init__(self):
        self.item = None
        self.ability = None
        self.pet = None   
        self.ground_item = None
    
def try_set_hover(item, rect):
    if item and rect.collidepoint(pygame.mouse.get_pos()):
        hover_state.item = item

hover_state = HoverState()
drag_state = DragState()
equipment = Equipment()

# ---------------------------------------------------------------
# REGISTRY - this system owns the shape; content/ fills it in.
# A system must NEVER import from content/.
# ---------------------------------------------------------------
base_items = {}
affix_pool = {}
affix_groups = {}
affix_count_by_rarity = {}

# ---------------------------------------------------------------
# AFFIX WEIGHTS AND GROUPS
#
# WEIGHT is how often an affix rolls compared to the others on that item.
# An affix sets its own with a "weight" key in affix_pool; without one it
# uses base_affix_weight.
#
# A GROUP is a name for several affixes, filled in content/items.py:
#
#     affix_groups.update({
#         "elemental_affixes": ["fire_damage", "fire_resistance", ...],
#     })
#
# A base item's "affixes" list takes an affix name, a GROUP name, or a
# (name, weight) pair to override the weight just for that item:
#
#     "affixes": ["elemental_affixes",        # the whole group, own weights
#                 ("fire_penetration", 40),   # this one, often, on this item
#                 ("lifesteal", 1)]           # this one, rarely
#
# A later entry wins, so list a group first and then override one member.
# ---------------------------------------------------------------
base_affix_weight = 10

def affix_entries(base):
    """base["affixes"] -> [(affix_key, weight), ...] with every group expanded.

    Three places can set the weight. The most specific one wins:
       1. the base item   ("fire_penetration", 40)
       2. the group       ("elemental_damage", 40) inside affix_groups
       3. the affix       "weight": 4 in affix_pool, else base_affix_weight
    """
    found = {}
    for entry in base["affixes"]:
        key, item_weight = entry if isinstance(entry, (tuple, list)) else (entry, None)
        for member in affix_groups.get(key, [key]):
            affix_key, group_weight = member if isinstance(member, (tuple, list)) else (member, None)
            affix = affix_pool.get(affix_key)
            if affix is None:
                print(f"WARNING: base item '{base.get('name')}' wants affix '{affix_key}',"
                      f" which is not in affix_pool. See content/items.py.")
                continue
            if item_weight is not None:
                found[affix_key] = item_weight
            elif group_weight is not None:
                found[affix_key] = group_weight
            else:
                found[affix_key] = affix.get("weight", base_affix_weight)
    return list(found.items())

# ---------------------------------------------------------------
# BASES THAT BUILD ON OTHER BASES (every unique does this)
#
#   "swarmcaller": {"base": "twig_wand", "name": "Swarmcaller", ...}
#
# Everything you write wins; everything you leave out comes from the base.
# ---------------------------------------------------------------
def resolve_base(key):
    """base_items[key] with its "base" filled in (and that base's base...)."""
    if key not in base_items:
        raise KeyError(f"No base item '{key}'. Base items live in content/items.py and content/uniques/.")
    base = base_items[key]
    parent = base.get("base")
    if parent is None:
        return base
    return {**resolve_base(parent), **base}

def reroll_unique(item):
    """Re-roll every range on an item that has fixed lines (a Divine Orb).
    Its random affixes, if any, are left alone. Returns True if it worked.
    Call player.recalculate_stats(force=True) afterwards if it is equipped."""
    from systems.bonuses import roll_bonuses
    base = resolve_base(item.base_key) if item.base_key in base_items else None
    if base is None:
        return False
    rolled = roll_bonuses(base)
    affixes = [line for line in item.stats if "tier" in line]
    item.stats = rolled.pop("stats", []) + affixes
    item.mods = [tuple(m) for m in rolled.get("mods", [])]
    item.grants = rolled.get("grants", {})
    item.effects = rolled.get("effects", {})
    item.summons = rolled.get("summons", {})
    return True

item_templates = {}

gem_built_in_support_chance = 1

def roll_gem_rarity():
    return roll_rarity({
        rarity_common:    50,
        rarity_uncommon:  25,
        rarity_rare:      14,
        rarity_epic:      7,
        rarity_legendary: 3,
    })

def roll_gem(template_key, rarity=None, sprite_name=None):
    from systems.abilities import active_gem_templates
    from systems.supports import support_gem_types
    t = active_gem_templates[template_key]
    if rarity is None:
        rarity = roll_gem_rarity()

    gem_stats = dict(t.get("rarity_stats", {}).get(rarity, {}))

    built_in = None
    if random.uniform(0, 100) < gem_built_in_support_chance:
        from systems.abilities import ability_tags, ability_blocked
        from systems.supports import support_fits
        tags, blocked = ability_tags(t), ability_blocked(t)
        compatible = [gt for gt in support_gem_types if support_fits(gt, tags, blocked)]
        if compatible:
            gem_type = random.choice(compatible)
            support_rarity = roll_rarity()
            built_in = SupportGem(gem_type, roll_support_value(gem_type, support_rarity), support_rarity)

    icon = sprite_name or t["sprite_name"]
    return ActiveGemItem(t["name"], icon, template_key, rarity=rarity, gem_stats=gem_stats, built_in_support=built_in)


def make_item(key, rarity=None):
    t = item_templates[key]
    kind = t["kind"]
    r = rarity if rarity is not None else t.get("rarity", rarity_common)

    if kind == "equippable":
        return EquippableItem(t["name"], t["sprite"], t["slot"], stats=t.get("stats"), rarity=r, weapon_class=t.get("weapon_class"), swing_sprite_name=t.get("swing_sprite"),
                              mods=t.get("mods"), grants=t.get("grants"), effects=t.get("effects"), summons=t.get("summons"))
    if kind == "active_gem":
        return roll_gem(t["template_key"], rarity=r, sprite_name=t.get("sprite"))
    if kind == "support_gem":
        return SupportGemItem(t["gem_type"], rarity=r)
    if kind == "pet":
        return PetItem(t["name"], t["sprite"], t["pet_type"], rarity=r)
    if kind == "currency":
        return Item(t["name"], t["sprite"], category=item_category_currency)

    raise ValueError(f"Unknown item kind '{kind}' for template '{key}'")
