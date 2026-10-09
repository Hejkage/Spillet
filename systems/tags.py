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
    from systems.skilltree import skill_nodes, adjacency
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
    for key, node in skill_nodes.items():
        check_bonuses(f"skill node '{key}' per_point", node["per_point"], problems)
        for at, bonus in node["at_points"].items():
            check_bonuses(f"skill node '{key}' at {at} points", bonus, problems)
            if at > node["max_points"]:
                problems.append(f"skill node '{key}': at_points {at} is more than max_points {node['max_points']}")
        for other in adjacency.get(key, ()):
            if other not in skill_nodes:
                problems.append(f"skill edge '{key}' - '{other}': '{other}' is not a skill node")

    if problems:
        raise ValueError("Problems found in content/:\n  " + "\n  ".join(problems))
