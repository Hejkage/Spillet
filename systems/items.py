import copy
import pygame
import random
from collections import Counter
from core.state import app, world
from core.screen import camera, get_font
from core.assets import sprites
from systems.rarity import rarity_colors, rarity_common, unique_color
from systems.weapons import get_weapon_geometry, player_body_radius, weapon_class_tags
from systems.supports import SupportGem, roll_support_value, support_gem_types
from core.assets import scaled_sprites
from systems.rarity import rarity_epic, rarity_legendary, rarity_rare, rarity_uncommon, roll_rarity

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

def register_equip_slot(name, group, accepts, background=None):
    equip_slots[name] = {"group": group, "accepts": accepts, "background": background}

def slots_in_group(group):
    return [n for n, d in equip_slots.items() if d["group"] == group]

def accepts_slot_type(t):
    return lambda item: getattr(item, "slot_type", None) == t

def accepts_gem(kind):
    return lambda item: getattr(item, "gem_slot", None) == kind


register_equip_slot("ring1",   "main", accepts_slot_type("ring"),    "inventory_slot_sprite")
register_equip_slot("ring2",   "main", accepts_slot_type("ring"),    "inventory_slot_sprite")
register_equip_slot("neck",    "main", accepts_slot_type("neck"),    "inventory_slot_sprite")
register_equip_slot("head",    "main", accepts_slot_type("head"),    "inventory_slot_helmet_sprite")
register_equip_slot("body",    "main", accepts_slot_type("body"),    "inventory_slot_body_sprite")
register_equip_slot("gloves",  "main", accepts_slot_type("gloves"),  "inventory_slot_sprite")
register_equip_slot("belt",    "main", accepts_slot_type("belt"),    "inventory_slot_sprite")
register_equip_slot("pants",   "main", accepts_slot_type("pants"),   "inventory_slot_pants_sprite")
register_equip_slot("boots",   "main", accepts_slot_type("boots"),   "inventory_slot_boots_sprite")
register_equip_slot("weapon",  "main", accepts_slot_type("weapon"),  "inventory_slot_sprite")
register_equip_slot("offhand", "main", accepts_slot_type("offhand"), "inventory_slot_sprite")

register_equip_slot("gem_active",   "extra", accepts_gem(gem_slot_active),  "inventory_slot_sprite")
register_equip_slot("gem_support1", "extra", accepts_gem(gem_slot_support), "inventory_slot_sprite")
register_equip_slot("gem_support2", "extra", accepts_gem(gem_slot_support), "inventory_slot_sprite")
register_equip_slot("gem_support3", "extra", accepts_gem(gem_slot_support), "inventory_slot_sprite")
register_equip_slot("gem_support4", "extra", accepts_gem(gem_slot_support), "inventory_slot_sprite")

register_equip_slot("pet1", "pet", lambda i: getattr(i, "is_pet", False), "inventory_slot_sprite")
register_equip_slot("pet2", "pet", lambda i: getattr(i, "is_pet", False), "inventory_slot_sprite")
register_equip_slot("pet3", "pet", lambda i: getattr(i, "is_pet", False), "inventory_slot_sprite")

main_equip_slots  = slots_in_group("main")
extra_equip_slots = slots_in_group("extra")
pet_equip_slots   = slots_in_group("pet")
active_gem_slot   = "gem_active"
support_gem_slots = [s for s in extra_equip_slots if s.startswith("gem_support")]

stat_defs = {}

def register_stat(key, label, base=0, percent=False, show_in_panel=True, panel_label=None):
    stat_defs[key] = {
        "label": label,
        "base": base,
        "percent": percent,
        "show_in_panel": show_in_panel,
        "panel_label": panel_label or label,
    }
    return key

register_stat("movement_speed",     "Movement Speed",           base=350)
register_stat("projectile_speed",   "Projectile Speed",         base=100, panel_label="Increased Projectile Speed")
register_stat("spell_damage",       "Spell Damage",             base=100, panel_label="Increased Spell Damage")
register_stat("attack_damage",      "Attack Damage",            base=100, panel_label="Increased Attack Damage")
register_stat("cooldown",           "Cooldown Reduction",       base=0,   percent=True)
register_stat("max_health",         "Health",                   base=1000)
register_stat("health_regen",       "Health Regen per Second",  base=5)
register_stat("lifesteal",          "Lifesteal",                base=0,   percent=True)
register_stat("crit_chance",        "Critical Strike Chance",   base=0,   percent=True)
register_stat("crit_damage",        "Critical Strike Damage",   base=150, percent=True)
register_stat("aoe",                "Area of Effect",           base=100, panel_label="Increased Area of Effect")
register_stat("physical_damage",    "Physical Damage",          base=100, show_in_panel=False)
register_stat("elemental_damage",   "Elemental Damage",         base=100, show_in_panel=False)
register_stat("attack_speed",       "Attack Speed",             base=100, panel_label="Increased Attack Speed")
register_stat("attack_range",       "Attack Range",             base=0,   show_in_panel=False)

def stat_label(key):
    return stat_defs[key]["label"] if key in stat_defs else key

def stat_is_percent(key):
    return key in stat_defs and stat_defs[key]["percent"]

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
        self.stats = copy.deepcopy(stats) if stats else {}
        self.category = category
        self.rarity = rarity

    def to_dict(self):
        return {"kind": self.save_kind, "name": self.name, "sprite_name": self.sprite_name, "rarity": self.rarity, "category": self.category}

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["sprite_name"], category=d.get("category", item_category_generic), rarity=d.get("rarity", rarity_common))

class EquippableItem(Item):
    save_kind = "equippable"

    def __init__(self, name, sprite_name, slot_type, layer_sprite_name=None, stats=None, rarity=rarity_common, weapon_class=None, swing_sprite_name=None):
        super().__init__(name, sprite_name, stats=stats, category=item_category_equipment, rarity=rarity)
        self.slot_type = slot_type
        self.layer_sprite_name = layer_sprite_name
        self.weapon_class = weapon_class
        self.swing_sprite_name = swing_sprite_name

    def to_dict(self):
        d = super().to_dict()
        d.update(slot_type=self.slot_type, layer_sprite_name=self.layer_sprite_name, stats=self.stats, weapon_class=self.weapon_class, swing_sprite=self.swing_sprite_name)
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["sprite_name"], d["slot_type"], layer_sprite_name=d.get("layer_sprite_name"), stats=d.get("stats", {}), rarity=d.get("rarity", rarity_common), weapon_class=d.get("weapon_class"), swing_sprite_name=d.get("swing_sprite"))

class GemItem(Item):
    def __init__(self, name, sprite_name, gem_slot, rarity=rarity_common):
        super().__init__(name, sprite_name, stats={}, category=item_category_equipment, rarity=rarity)
        self.gem_slot = gem_slot

class ActiveGemItem(GemItem):
    save_kind = "active_gem"

    def __init__(self, name, sprite_name, template_key, rarity=rarity_common, gem_stats=None, built_in_support=None):
        super().__init__(name, sprite_name, gem_slot_active, rarity)
        self.template_key = template_key
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
        return d

    @classmethod
    def from_dict(cls, d):
        built_in = None
        bi = d.get("built_in_support")
        if bi is not None:
            built_in = SupportGem(bi["gem_type"], bi["value"], bi["rarity"])
        return cls(d["name"], d["sprite_name"], d["template_key"], rarity=d.get("rarity", rarity_common), gem_stats=d.get("gem_stats", {}), built_in_support=built_in)

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

class PetItem(Item):
    save_kind = "pet"

    def __init__(self, name, sprite_name, pet_type, rarity=rarity_common):
        super().__init__(name, sprite_name, category=item_category_generic, rarity=rarity)
        self.pet_type = pet_type
        self.is_pet = True

    def to_dict(self):
        d = super().to_dict()
        d["pet_type"] = self.pet_type
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["sprite_name"], d["pet_type"], rarity=d.get("rarity", rarity_common))

class UniqueItem(EquippableItem):
    """A unique item. Its random parts are rolled ONCE when the item is made
    (dropped / put in a shop) and stored in self.rolled, which is saved with the
    item. They never change again unless reroll_unique() is called on it
    (e.g. by a Divine Orb-style currency). See register_unique() below."""
    save_kind = "unique"

    def __init__(self, name, sprite_name, slot_type, layer_sprite_name=None, stats=None, weapon_class=None, summon_pets=None, swing_sprite_name=None, unique_key=None):
        super().__init__(name, sprite_name, slot_type, layer_sprite_name=layer_sprite_name, stats=stats, rarity=rarity_common, weapon_class=weapon_class, swing_sprite_name=swing_sprite_name)
        self.summon_pets = list(summon_pets) if summon_pets else []
        self.is_unique = True
        self.unique_key = unique_key
        self.rolled = {}

    def apply_rolled(self, rolled):
        """Store rolled values and put them on the item (rolled["summon_pets"] -> self.summon_pets)."""
        self.rolled = copy.deepcopy(rolled)
        for attr, value in self.rolled.items():
            setattr(self, attr, copy.deepcopy(value))

    def to_dict(self):
        d = super().to_dict()
        d["summon_pets"] = self.summon_pets
        d["unique_key"] = self.unique_key
        # Save what the item has NOW (not the original roll), so later changes
        # to e.g. item.summon_pets are saved too.
        d["rolled"] = {attr: getattr(self, attr) for attr in self.rolled}
        return d

    @classmethod
    def from_dict(cls, d):
        item = cls(d["name"], d["sprite_name"], d["slot_type"], layer_sprite_name=d.get("layer_sprite_name"), stats=d.get("stats", {}), weapon_class=d.get("weapon_class"), summon_pets=d.get("summon_pets", []), swing_sprite_name=d.get("swing_sprite"), unique_key=d.get("unique_key"))
        if item.unique_key is None:
            # Saves from before unique_key existed: find the template by name.
            item.unique_key = next((k for k, t in unique_templates.items() if t["name"] == item.name), None)
        if d.get("rolled"):
            item.apply_rolled(d["rolled"])
        return item

# ---------------------------------------------------------------
# UNIQUES - fixed base + a roll function for the random parts.
#
#   register_unique("swarmcaller", roll=roll_swarmcaller_pets,
#                   name="Swarmcaller", sprite_name="wand_item_sprite",
#                   slot_type="weapon", weapon_class="wand")
#
# roll() returns a dict of the random parts, e.g. {"summon_pets": [...]}.
# Each key becomes an attribute on the item and is saved with it.
# ---------------------------------------------------------------
unique_templates = {}

def register_unique(key, roll=None, **base):
    """base = everything UniqueItem takes (name, sprite_name, slot_type, stats...)."""
    if key in unique_templates:
        raise ValueError(f"Unique '{key}' is registered twice")
    unique_templates[key] = {"roll": roll, **base}
    return key

def make_unique(key):
    """Create a new copy of a unique and roll its random parts."""
    t = {k: copy.deepcopy(v) for k, v in unique_templates[key].items() if k != "roll"}
    roll = unique_templates[key]["roll"]
    item = UniqueItem(unique_key=key, **t)
    if roll:
        item.apply_rolled(roll())
    return item

def reroll_unique(item):
    """Re-roll the random parts of an existing unique (Divine Orb). Returns True if it worked."""
    t = unique_templates.get(getattr(item, "unique_key", None))
    if not t or not t["roll"]:
        return False
    item.apply_rolled(t["roll"]())
    return True

class Equipment:
    def __init__(self):
        self.main_slots = {slot: None for slot in main_equip_slots}
        self.extra_slots = {slot: None for slot in extra_equip_slots}
        self.pet_slots = {slot: None for slot in pet_equip_slots}
        self.open = False
        self.drag_source = None
        self.rect = None

    def toggle(self):
        self.open = not self.open
    
    def can_equip(self, item, slot_name):
        d = equip_slots.get(slot_name)
        return bool(d) and d["accepts"](item)
    
    def draw(self, scaled_sprites, player):
        if not self.open:
            return

        scale = app.ui_scale
        slot_size = max(1, int(equip_slot_size * scale))
        padding = max(1, int(equip_padding * scale))
        outer_margin = max(1, int(30 * scale))

        left_slots = ["head", "body", "pants", "boots",]
        right_slots = ["ring1", "ring2", "gloves", "neck", "belt"]
        bottom_slots = ["weapon", "offhand"]

        # gap between adjacent columns
        col_gap = slot_size + padding * 3

        # four columns: left(main), right(main), pet, extra
        num_columns = 4
        # tallest main column decides the vertical space needed
        tallest = max(len(left_slots), len(right_slots), len(pet_equip_slots), len(extra_equip_slots))

        # panel sized to actually fit the columns + a bottom row
        panel_width = outer_margin * 2 + num_columns * slot_size + (num_columns - 1) * col_gap
        panel_height = outer_margin * 2 + tallest * (slot_size + padding) + (slot_size + padding * 2)

        panel_x = app.screen_width // 2 - panel_width // 2
        panel_y = app.screen_height // 2 - panel_height // 2
        self.rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        bg_surface = pygame.transform.scale(scaled_sprites["inventory_background_sprite"], (panel_width, panel_height))
        app.screen.blit(bg_surface, (panel_x, panel_y))

        self.draw_stat_panel(scaled_sprites, player, panel_x, panel_y, panel_height, scale)

        self.slot_size = slot_size
        self.padding = padding

        # column x positions derived from slot size, so they never overlap
        col_x = [panel_x + outer_margin + c * (slot_size + col_gap) for c in range(num_columns)]
        top_y = panel_y + outer_margin

        self.main_slot_rects = {}

        for i, slot in enumerate(left_slots):
            rect = pygame.Rect(col_x[0], top_y + i * (slot_size + padding), slot_size, slot_size)
            self.main_slot_rects[slot] = rect
            self.draw_slot(scaled_sprites, rect, self.main_slots[slot], slot)

        for i, slot in enumerate(right_slots):
            rect = pygame.Rect(col_x[1], top_y + i * (slot_size + padding), slot_size, slot_size)
            self.main_slot_rects[slot] = rect
            self.draw_slot(scaled_sprites, rect, self.main_slots[slot], slot)

        self.pet_slots_rects = {}
        for i, slot in enumerate(pet_equip_slots):
            rect = pygame.Rect(col_x[2], top_y + i * (slot_size + padding), slot_size, slot_size)
            self.pet_slots_rects[slot] = rect
            self.draw_slot(scaled_sprites, rect, self.pet_slots[slot], slot)

        self.extra_slots_rects = {}
        for i, slot in enumerate(extra_equip_slots):
            rect = pygame.Rect(col_x[3], top_y + i * (slot_size + padding), slot_size, slot_size)
            self.extra_slots_rects[slot] = rect
            self.draw_slot(scaled_sprites, rect, self.extra_slots[slot], slot)

        # weapon / offhand centered along the bottom of the panel
        bottom_y = panel_y + panel_height - outer_margin - slot_size
        bottom_total_width = len(bottom_slots) * slot_size + (len(bottom_slots) - 1) * padding
        bottom_start_x = panel_x + panel_width // 2 - bottom_total_width // 2

        for i, slot in enumerate(bottom_slots):
            x = bottom_start_x + i * (slot_size + padding)
            rect = pygame.Rect(x, bottom_y, slot_size, slot_size)
            self.main_slot_rects[slot] = rect
            self.draw_slot(scaled_sprites, rect, self.main_slots[slot], slot)

    def draw_slot(self, scaled_sprites, rect, item, slot_name=None):
        bg_name = equip_slots.get(slot_name, {}).get("background") or "inventory_slot_sprite"
        slot_sprite = scaled_sprites.get(bg_name) or scaled_sprites.get("inventory_slot_sprite")
        if slot_sprite:
            scaled_slot = pygame.transform.scale(slot_sprite, (rect.width, rect.height))
            app.screen.blit(scaled_slot, rect)

        if item:
            item_sprite = scaled_sprites.get(item.sprite_name)
            if item_sprite:
                fitted = scale_item_sprite(item_sprite, rect.width * 0.9)
                app.screen.blit(fitted, fitted.get_rect(center=rect.center))

        try_set_hover(item, rect)

    def draw_stat_panel(self, scaled_sprites, player, panel_x, panel_y, panel_height, scale):
        panel_width = int(350 * scale)
        stats_x = panel_x - panel_width - int(10 * scale)

        bg_surface = pygame.transform.scale(scaled_sprites["inventory_background_sprite"], (panel_width, panel_height))
        app.screen.blit(bg_surface, (stats_x, panel_y))

        font_size = max(15, int(25 * scale))
        font = get_font(font_size)

        row_padding = int(20 * scale)
        text_x = stats_x + row_padding

        i = 0
        for stat, d in stat_defs.items():
            if not d["show_in_panel"]:
                continue

            label = d["panel_label"]
            value = getattr(player, stat, 0)

            if stat == "crit_chance":
                value = player.increased["crit_chance"] * 100
                label = "Increased critical strike chance"

            if d["base"] == 100:
                value -= 100

            rounded = round(value, 2)
            display_value = str(int(rounded)) if rounded == int(rounded) else f"{rounded:.2f}"

            suffix = "%" if (d["percent"] or d["base"] == 100) else ""
            text = font.render(f"{label}: {display_value}{suffix}", True, (255, 255, 255))
            app.screen.blit(text, (text_x, panel_y + row_padding + i * font_size))
            i += 1
                            
    def handle_click(self, pos, button, drag_state, player):
        if not self.open or button != 1:
            return False
        
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

@tooltip_section
def _tt_stats(item, lines):
    for mod in item.stats.values():
        stat = mod.get("stat")
        label = stat_label(stat)              
        amount = mod.get("amount", 0)
        color = rarity_colors.get(mod.get("tier"), _WHITE)
        mod_type = mod.get("type")
        if mod_type == "flat":
            suffix = "%" if stat_is_percent(stat) else ""  
            lines.append((f"+{amount}{suffix} {label}", color))
        elif mod_type == "increased":
            lines.append((f"+{int(amount)}% increased {label}", color))
        elif mod_type == "more":
            lines.append((f"+{amount}% {label}", color))
        else:
            lines.append((f"{amount} {label}", color))

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
def _tt_summons(item, lines):
    from systems.pets import pet_display_name
    if getattr(item, "is_unique", False):
        summon = getattr(item, "summon_pets", [])
        for pet_type, n in Counter(summon).items():
            lines.append((f"Summons {n} {pet_display_name(pet_type, n)}", _WHITE))

@tooltip_section
def _tt_support_gem(item, lines):
    if hasattr(item, "support_gem"):
        lines.append((item.support_gem.describe(), _WHITE))

@tooltip_section
def _tt_active_gem(item, lines):
    from systems.abilities import active_gem_templates, template_uses_aoe
    if not hasattr(item, "template_key"):
        return
    t = active_gem_templates[item.template_key]
    rolled = getattr(item, "gem_stats", {})

    def gem_val(stat, default=None):
        return rolled.get(stat, t.get(stat, default))

    dmg = gem_val("damage")
    if dmg is not None:
        lines.append((f"{dmg:.0f} damage", _WHITE))

    speed_stat = t.get("speed_stat")
    cd = gem_val("attack_time")
    if cd is None:
        cd = gem_val("cooldown")
    if cd is not None:
        label = "attack time" if speed_stat else "cooldown"
        lines.append((f"{cd:.2f}s {label}", _WHITE))

    speed = gem_val("projectile_speed")
    if speed is not None:
        lines.append((f"{speed:.0f} projectile speed", _WHITE))

    gem_aoe = gem_val("aoe")
    if gem_aoe is not None and template_uses_aoe(t):
        lines.append((f"{gem_aoe * 100:.0f}% area of effect", _WHITE))

    cc = gem_val("crit_chance", 0)
    if cc:
        lines.append((f"{cc:.0f}% crit chance", _WHITE))

    cdmg = gem_val("crit_damage", 0)
    if cdmg:
        lines.append((f"{cdmg:.0f}% crit damage", _WHITE))

    dot_d = gem_val("dot_damage", 0)
    if dot_d:
        lines.append((f"{dot_d:.0f} damage per second", _WHITE))
        dot_dur = gem_val("dot_duration", 0)
        if dot_dur:
            lines.append((f"{dot_dur:.0f}s damage over time", _WHITE))

    scaling = t.get("damage_scaling")
    if scaling:
        nice = ", ".join(stat_label(s).lower() for s in scaling)   # was stat_display.get
        lines.append((f"Scales with: {nice}", _GRAY))

    built_in = getattr(item, "built_in_support", None)
    if built_in is not None:
        color = rarity_colors.get(built_in.rarity, _WHITE)
        lines.append((f"Built-in: {built_in.describe()}", color))

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
    name_color = unique_color if getattr(item, "is_unique", False) else rarity_colors.get(item.rarity, _WHITE)
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
affix_count_by_rarity = {}
item_templates = {}
# ---------------------------------------------------------------
# Gem rolling. This is a MECHANIC (it builds an item object), so it
# lives in systems/. The gem definitions it reads live in content/gems.py.
# ---------------------------------------------------------------
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
        allowed_tags = t.get("support_tags", set())
        compatible = [gt for gt, cfg in support_gem_types.items() if cfg["tags"] & allowed_tags]
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
        return EquippableItem(t["name"], t["sprite"], t["slot"], stats=t.get("stats"), rarity=r, weapon_class=t.get("weapon_class"), swing_sprite_name=t.get("swing_sprite"))
    if kind == "active_gem":
        return roll_gem(t["template_key"], rarity=r, sprite_name=t.get("sprite"))
    if kind == "support_gem":
        return SupportGemItem(t["gem_type"], rarity=r)
    if kind == "pet":
        return PetItem(t["name"], t["sprite"], t["pet_type"], rarity=r)
    if kind == "currency":
        return Item(t["name"], t["sprite"], category=item_category_currency)

    raise ValueError(f"Unknown item kind '{kind}' for template '{key}'")
