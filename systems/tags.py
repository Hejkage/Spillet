"""TAGS - the one list of words every system uses to describe hits and abilities.

A tag says WHAT something is: "fire", "spell", "projectile", "melee"...
The same words are used everywhere:

  abilities   work out their own tags (see ability_tags in systems/abilities.py):
              a fireball is {"spell", "projectile", "fire", "elemental", "aoe", "damage", "caster"}
  mods and    say what they NEED:  pierce needs {"projectile"}
  supports    and what damage they ADD: added fire scales {"fire"}
  "blocked"   on an ability or pet: it can't scale with these, and supports that
              need or add them can't be socketed:  "blocked": {"elemental"}
  stats       are named from tags: fire_resistance, spell_damage, elemental_penetration
  enemies     resist by tag ("defence") and are immune by status name ("immune")

Damage types and their groups ("fire" is "elemental") come from damage_types in
systems/damage.py, so a new damage type is still one line there.
Every other tag is one register_tag() line below.

check_all_content() runs once after content/ has loaded. A typo such as
"elemenal" stops the game at start-up with a clear message, instead of silently
doing nothing.
"""
from systems.damage import damage_types, damage_groups

known_tags = {}          # tag -> description

def register_tag(name, description=""):
    known_tags[name] = description
    return name

# --- damage types and groups (from systems/damage.py) -----------------------
for _t in damage_types:
    register_tag(_t, "damage type")
for _g in damage_groups:
    register_tag(_g, "damage group")

# --- what kind of hit -------------------------------------------------------
register_tag("attack",     "a weapon hit: attack speed, attack crit")
register_tag("spell",      "a cast: cooldown reduction, spell crit, silence blocks it")
register_tag("damage",     "deals damage at all")

# --- how it hits ------------------------------------------------------------
register_tag("projectile", "fires projectiles")
register_tag("melee",      "a melee swing / a melee weapon")
register_tag("aoe",        "its size scales with area of effect")
register_tag("dot",        "deals damage over time")

# --- weapons (weapon_class_configs in content/items.py) ---------------------
register_tag("caster",     "wands, staffs")
register_tag("ranged",     "bows, guns")
register_tag("one_hand")
register_tag("two_hand")


# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------
# How tags are shown to the player, in this order. A tag not listed here is shown
# after these, with its name in Title Case ("one_hand" -> "One Hand").
tag_display = [("attack", "Attack"), ("spell", "Spell"), ("projectile", "Projectile"), ("melee", "Melee"),
               ("aoe", "Area"), ("dot", "Damage over Time")]
hidden_tags = {"damage"}     # every damaging ability has it - not worth a word

def tag_line(tags, blocked=()):
    """ "Tags: Spell, Projectile, Area, Fire, Elemental" - what an ability IS, and so what
    scales it. A tag it blocks is left out, because nothing with that tag scales it."""
    shown = set(tags) - with_members(blocked) - hidden_tags
    order = [label for key, label in tag_display if key in shown]
    order += [t.title() for t in damage_types if t in shown]                     # its damage types
    order += [g.title() for g in damage_groups if g in shown]                    # their groups
    known = {key for key, _ in tag_display} | set(damage_types) | set(damage_groups)
    order += [t.replace("_", " ").title() for t in sorted(shown - known)]        # weapon tags...
    return "Tags: " + ", ".join(order) if order else ""

def with_groups(tags):
    """Add the group of every damage type: {"fire"} -> {"fire", "elemental"}."""
    tags = set(tags or ())
    for t in list(tags):
        tags |= set(damage_types.get(t, ()))
    return tags

def with_members(tags):
    """Add every damage type inside a group: {"elemental"} -> {"elemental", "fire", "frost", "nature"}."""
    tags = set(tags or ())
    for t, groups in damage_types.items():
        if tags & set(groups):
            tags.add(t)
    return tags

def fits(needs, scales, ability_tags, blocked):
    """Can a mod / support land on this ability?
    needs    every one of these must be in the ability's tags
    scales   the damage types it adds (added fire -> {"fire"})
    blocked  the ability's "blocked" set (groups already expanded)
    Refused if it needs or adds anything the ability blocks."""
    needs = set(needs or ())
    if not needs <= set(ability_tags or ()):
        return False
    touched = with_groups(needs | set(scales or ()))
    return not (touched & set(blocked or ()))


# ---------------------------------------------------------------
# START-UP CHECK
# ---------------------------------------------------------------
def unknown(tags):
    return sorted(set(tags or ()) - set(known_tags))

def check_all_content():
    """Look through everything content/ registered and list every unknown tag,
    missing field or misspelled defence key. Raises ONE error with all of them."""
    from systems.abilities import active_gem_templates, basic_attack_templates
    from systems.mods import mod_types
    from systems.supports import support_gem_types
    from systems.weapons import weapon_class_configs
    from systems.pets import pet_configs
    from systems.enemies import enemy_configs
    from systems.status import status_effect_types
    problems = []

    def bad(where, tags):
        for tag in unknown(tags):
            problems.append(f"{where}: unknown tag '{tag}'")

    for kind, templates in (("gem", active_gem_templates), ("basic attack", basic_attack_templates)):
        for key, t in templates.items():
            where = f"{kind} '{key}'"
            if t.get("hit_type") not in ("attack", "spell"):
                problems.append(f"{where}: needs \"hit_type\": \"attack\" or \"spell\"")
            bad(where, t.get("tags"))
            bad(where + " blocked", t.get("blocked"))
            bad(where + " weapon_tags", t.get("weapon_tags"))
            bad(where + " damage", list(t.get("damage_split", {})) + [t.get("damage_type", "physical")])
            for old in ("support_tags", "damage_scaling", "cannot_scale", "crit_type", "danage_type"):
                if old in t:
                    problems.append(f"{where}: \"{old}\" is not used any more - see systems/tags.py")

    for name, m in mod_types.items():
        bad(f"mod '{name}' needs", m["needs"])
        bad(f"mod '{name}' scales", m["scales"])
    for name, s in support_gem_types.items():
        bad(f"support '{name}' needs", s["needs"])

    for name, w in weapon_class_configs.items():
        bad(f"weapon class '{name}'", w.get("tags"))

    for name, p in pet_configs.items():
        stats = p["stats"]
        if stats.get("hit_type", "attack") not in ("attack", "spell"):
            problems.append(f"pet '{name}': hit_type must be \"attack\" or \"spell\"")
        bad(f"pet '{name}' blocked", stats.get("blocked"))
        bad(f"pet '{name}' damage", [stats.get("damage_type", "physical")])

    defence_types = set(damage_types) | set(damage_groups)
    for name, e in enemy_configs.items():
        for key in e.get("defence", {}):
            tag, _, suffix = key.rpartition("_")
            if tag not in defence_types or suffix not in ("resistance", "protection"):
                problems.append(f"enemy '{name}': defence '{key}' should be <damage type or group>_resistance / _protection")
        for status in e.get("immune", ()):
            if status not in status_effect_types:
                problems.append(f"enemy '{name}': immune to unknown status '{status}'")

    from systems.items import immunity_stats
    for stat, status in immunity_stats.items():
        if status not in status_effect_types:
            problems.append(f"register_immunity: unknown status '{status}'")

    for name, s in status_effect_types.items():
        bad(f"status '{name}' blocks", s["blocks"])

    # items and skill tree nodes: unknown stats, mods, effects, pets, bases
    from systems.items import base_items, item_templates, resolve_base
    from systems.bonuses import check_bonuses
    from systems.rarity import all_rarities
    for key, base in base_items.items():
        where = f"item '{key}'"
        try:
            full = resolve_base(key)
        except KeyError:
            problems.append(f"{where}: \"base\": '{base.get('base')}' is not a base item")
            continue
        for field in ("name", "sprite", "slot"):
            if field not in full:
                problems.append(f"{where}: needs \"{field}\"")
        if "rarity" in full and full["rarity"] not in all_rarities:
            problems.append(f"{where}: unknown rarity '{full['rarity']}'")
        check_bonuses(where, full, problems)
    for key, t in item_templates.items():
        if t.get("kind") == "equippable":
            check_bonuses(f"item '{key}'", t, problems)
    # costs and requirements: unknown resources / attributes
    from systems.resources import resource_types
    from systems.attributes import attribute_types
    def check_requires(where, requires):
        for key in requires or {}:
            if key != "level" and key not in attribute_types:
                problems.append(f"{where}: requires unknown attribute '{key}' (attributes: {sorted(attribute_types)}, or 'level')")
    for key, t in active_gem_templates.items():
        check_requires(f"gem '{key}'", t.get("requires"))
        costs = [t.get("cost") or {}] + [row.get("cost") or {} for row in t.get("rarity_stats", {}).values()]
        for cost in costs:
            for resource in cost:
                if resource not in resource_types:
                    problems.append(f"gem '{key}': costs unknown resource '{resource}' (resources: {sorted(resource_types)})")
    for key in base_items:
        try:
            check_requires(f"item '{key}'", resolve_base(key).get("requires"))
        except KeyError:
            pass                                       # a bad "base" is already reported above
    for key, p in pet_configs.items():
        check_requires(f"pet '{key}'", p.get("requires"))
    for key, config in attribute_types.items():
        check_bonuses(f"attribute '{key}' per_point", config["per_point"], problems)
        for at, bonus in config["checkpoints"].items():
            check_bonuses(f"attribute '{key}' at {at}", bonus, problems)

    # every tree: the passive tree, every gem tree, every pet tree
    from systems.trees import trees
    for tree in trees.values():
        for key, node in tree.nodes.items():
            where = f"tree '{tree.key}', node '{key}'"
            tables = node["choices"] or [node]                 # a choice node: check every option
            for at, bonus in [(at, b) for t in tables for at, b in [("per_point", t["per_point"])] + list(t["at_points"].items())]:
                if tree.owner == "pet":                # pet stat names were checked when the node was made
                    bonus = {part: value for part, value in bonus.items() if part != "mods"}
                check_bonuses(f"{where} at {at}", bonus, problems)
                if at != "per_point" and at > node["max_points"]:
                    problems.append(f"{where}: at_points {at} is more than max_points {node['max_points']}")
        for key, others in tree.adjacency.items():
            for other in [key] + others:
                if other not in tree.nodes:
                    problems.append(f"tree '{tree.key}': a line goes to '{other}', which is not a node")
        if tree.nodes and not tree.roots():
            problems.append(f"tree '{tree.key}': has no is_root node, so nothing can ever be allocated")
        for section in tree.sections:
            roots = [k for k in tree.section_nodes(section) if tree.nodes[k]["is_root"]]
            if len(roots) != 1:
                problems.append(f"tree '{tree.key}': section '{section}' needs exactly one is_root node, has {len(roots)}")

    if problems:
        raise ValueError("Problems found in content/:\n  " + "\n  ".join(problems))
