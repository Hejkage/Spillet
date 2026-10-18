"""ATTRIBUTES - Creation, Domination, Efficiency... (registered in content/attributes.py)

An attribute is a normal STAT (items, the tree, pets' auras give it like any
other stat) that ALSO gives bonuses of its own, in the same format as a skill
tree node:

    register_attribute("domination", "Domination",
        per_point={"mods": [("max_health", 2)]},
        checkpoints={
            100: {"mods": [("increased_physical_damage", 10)]},
            500: {"grants": {"pet_slots": 1}},
        })

per_point    given for every point you have
every        given once per FULL step of points: {10: {"mods": [("increased_pet_buff_effect", 1)]}}
             = 1% per 10 points (15 points = 1%, 20 points = 2%)
checkpoints  given once you reach that many points. Every checkpoint reached counts.
Both use the five parts from systems/bonuses.py: stats, mods, grants, effects, summons.
An attribute's bonuses can NOT give attributes (it would raise itself forever).

REQUIREMENTS: items, gems and pets can need attributes (or a level):
    "requires": {"domination": 300, "level": 20}
An item's own attributes count towards its own requirement. You can't equip
what you don't meet, and an equipped item that stops meeting it turns red and
does nothing (systems/items.py, equip rules).
"""
from systems.items import register_stat, equip_rule, stat_tabs, panel_rows, tooltip_sections
from systems.bonuses import scale_part, add_part, describe_bonuses

attribute_types = {}

stat_tabs.append(("attributes", "Attributes"))      # its own tab in the stats panel

def register_attribute(key, label, per_point=None, checkpoints=None, color=None, description="", every=None):
    register_stat(key, label, base=0, tab="attributes", always=True, color=color)
    attribute_types[key] = {
        "label": label,
        "per_point": per_point or {},
        "every": {int(k): dict(v) for k, v in (every or {}).items()},
        "checkpoints": {int(k): dict(v) for k, v in (checkpoints or {}).items()},
        "description": description,
    }
    return key

def attribute_label(key):
    if key == "level":
        return "Level"
    return attribute_types[key]["label"] if key in attribute_types else key


# ---------------------------------------------------------------
# VALUES AND BONUSES
# ---------------------------------------------------------------
def attribute_values(stat_lines):
    """{attribute: value} from a list of stat lines: (flat) * (1 + increased)."""
    flat, increased = {}, {}
    for line in stat_lines:
        key = line.get("stat")
        if key in attribute_types:
            if line.get("type") == "increased":
                increased[key] = increased.get(key, 0) + line.get("amount", 0) / 100
            else:
                flat[key] = flat.get(key, 0) + line.get("amount", 0)
    return {key: max(0, flat.get(key, 0) * (1 + increased.get(key, 0))) for key in attribute_types}

def attribute_lines(sources):
    """[(source_key, stat line), ...] - every attribute line from these sources."""
    from systems.bonuses import get_part
    return [(key, line) for key, source in sources for line in (get_part(source, "stats") or ())
            if line.get("stat") in attribute_types]

def attribute_bonuses(values):
    """{part: ...} - everything your attribute values give, all attributes together."""
    total = {}
    for key, config in attribute_types.items():
        points = int(values.get(key, 0))
        if points <= 0:
            continue
        for part, value in config["per_point"].items():
            add_part(total, part, scale_part(part, value, points))
        for step, bonus in config.get("every", {}).items():
            times = points // step                        # full steps only
            if times > 0:
                for part, value in bonus.items():
                    add_part(total, part, scale_part(part, value, times))
        for at, bonus in sorted(config["checkpoints"].items()):
            if at <= points:
                for part, value in bonus.items():
                    add_part(total, part, value)
    # the rule: attributes never raise attributes
    total["stats"] = [line for line in total.get("stats", []) if line.get("stat") not in attribute_types]
    return total

def next_checkpoint(key, value):
    """(points, bonus) of the next checkpoint not reached yet, or None."""
    for at, bonus in sorted(attribute_types[key]["checkpoints"].items()):
        if at > value:
            return at, bonus
    return None


# ---------------------------------------------------------------
# REQUIREMENTS
# ---------------------------------------------------------------
def item_requirements(item):
    """{"domination": 300, "level": 20} for any item: gear, gems and pets."""
    if item is None:
        return {}
    own = getattr(item, "requires", None)
    if own:
        return own
    from systems.items import base_items, resolve_base
    base_key = getattr(item, "base_key", None)
    if base_key in base_items:
        return resolve_base(base_key).get("requires", {})
    pet_type = getattr(item, "pet_type", None)                  # before gems: pets have a tree key too
    if pet_type:
        from systems.pets import pet_configs
        return pet_configs.get(pet_type, {}).get("requires", {})
    template_key = getattr(item, "template_key", None)
    if template_key:
        from systems.abilities import active_gem_templates
        return active_gem_templates.get(template_key, {}).get("requires", {})
    return {}

def attributes_with(player, item, slot_name, equipment):
    """Your attributes as they WOULD be with `item` in `slot_name` - its own
    attributes count, and whatever it replaces stops counting."""
    if slot_name is None or equipment.item_in(slot_name) is item:
        return getattr(player, "attributes", {})               # already worn: already counted
    replaced = id(equipment.item_in(slot_name)) if equipment.item_in(slot_name) is not None else None
    lines = [line for source, line in getattr(player, "attribute_lines", []) if source != replaced]
    from systems.bonuses import get_part
    lines += [line for line in (get_part(item, "stats") or []) if line.get("stat") in attribute_types]   # "mods" too
    return attribute_values(lines)

def missing_requirements(item, player, slot_name=None, equipment=None):
    """[(key, needed, have), ...] for every requirement not met."""
    missing = []
    needs = item_requirements(item)
    if not needs:
        return missing
    attributes = attributes_with(player, item, slot_name, equipment) if equipment else getattr(player, "attributes", {})
    for key, needed in needs.items():
        have = player.level if key == "level" else attributes.get(key, 0)
        if have < needed:
            missing.append((key, needed, have))
    return missing

@equip_rule
def _requirements(equipment, item, slot_name, player):
    """Not enough Domination / level -> can't equip it, or it turns red."""
    missing = missing_requirements(item, player, slot_name, equipment)
    if missing:
        key, needed, _ = missing[0]
        return f"Requires {needed:g} {attribute_label(key)}"
    return None

def _tt_requirements(item, lines):
    """'Requires 300 Domination, Level 20' under the item name. Red if not met."""
    needs = item_requirements(item)
    if not needs:
        return
    from systems.player import player
    missing = {key for key, _, _ in missing_requirements(item, player)}
    text = ", ".join(f"{attribute_label(k)} {v:g}" if k == "level" else f"{v:g} {attribute_label(k)}"
                     for k, v in needs.items())
    lines.append((f"Requires {text}", (220, 80, 80) if missing else (170, 170, 170)))

tooltip_sections.insert(0, _tt_requirements)           # right under the item name


# ---------------------------------------------------------------
# STATS PANEL - what each attribute gives you now, and the next checkpoint
# ---------------------------------------------------------------
@panel_rows("attributes")
def _rows_attribute_bonuses(player):
    rows = []
    values = getattr(player, "attributes", {})
    given = describe_bonuses(attribute_bonuses(values))
    if given:
        rows.append(("", (255, 255, 255)))
        rows.append(("From your attributes:", (255, 255, 255)))
        rows += [(text, (200, 200, 200)) for text in given]
    for key, config in attribute_types.items():
        upcoming = next_checkpoint(key, int(values.get(key, 0)))
        if upcoming:
            at, bonus = upcoming
            for text in describe_bonuses(bonus):
                rows.append((f"{config['label']} {at}: {text}", (150, 150, 160)))
    return rows