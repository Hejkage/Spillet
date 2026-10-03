skill_nodes = {}
adjacency = {}
allocated_nodes = set()
pending_nodes = set()      # what's being edited while the tree panel is open

respec_cost_per_node = 25  # gold to unallocate one node

def register_skill_node(key, name, position, stats=None, mods=None,
                        grants=None, effects=None, description=None,
                        is_root=False, sprite_name=None):
    """description = your own text, shown under the name in the tooltip.
    The mechanics (stats/mods/grants/effects) already describe themselves, so
    use description to explain WHY the node exists, not what it does."""
    skill_nodes[key] = {
        "name": name,
        "stats": stats or [],
        "mods": list(mods or []),
        "grants": grants or {},
        "effects": {event: list(data) for event, data in (effects or {}).items()},
        "description": description or "",
        "position": position,
        "is_root": is_root,
        "sprite_name": sprite_name,
    }
    return key

# ---------------------------------------------------------------
# WHAT THE ALLOCATED NODES ADD UP TO.
# The player rebuilds these in recalculate_stats(), so every other system
# reads them off the player and never from this module.
# ---------------------------------------------------------------
def allocated_mods():
    """-> [(name, value), ...] applied to every ability the player uses."""
    from systems.mods import mod_types
    found = []
    for key in allocated_nodes:
        for name, value in skill_nodes[key]["mods"]:
            if name in mod_types:
                found.append((name, value))
            else:
                print(f"WARNING: skill node '{key}' wants mod '{name}',"
                      f" which is not registered. See systems/mods.py.")
    return found

def allocated_grants():
    """-> {name: total}. Numbers add up; True counts as 1 and stays truthy."""
    totals = {}
    for key in allocated_nodes:
        for name, value in skill_nodes[key]["grants"].items():
            totals[name] = totals.get(name, 0) + (1 if value is True else value)
    return totals

def allocated_effects():
    """-> {event: [effect dict, ...]} from every allocated node."""
    events = {}
    for key in allocated_nodes:
        for event, data in skill_nodes[key]["effects"].items():
            events.setdefault(event, []).extend(data)
    return events

# ---------------------------------------------------------------
# WHAT A NODE SAYS IT DOES
#
# Every line is asked of the registry that owns the thing, so a new mod,
# effect or stat describes itself and no description is written twice.
#
# Grant names are turned into a label automatically ("ring_slots" ->
# "Ring slots"). Override one with register_grant_label().
# ---------------------------------------------------------------
grant_labels = {}

def register_grant_label(name, label):
    grant_labels[name] = label

def grant_label(name):
    return grant_labels.get(name) or name.replace("_", " ").capitalize()

def node_lines(key):
    """-> [str, ...] describing everything this node does."""
    from systems.items import stat_label, stat_is_percent
    from systems.mods import describe_mod
    from systems.status import describe_effect

    data = skill_nodes[key]
    lines = []

    for mod in data["stats"]:
        stat = mod.get("stat")
        amount = mod.get("amount", 0)
        label = stat_label(stat)
        if mod.get("type") == "increased":
            lines.append(f"+{amount:g}% increased {label}")
        else:
            suffix = "%" if stat_is_percent(stat) else ""
            lines.append(f"+{amount:g}{suffix} {label}")

    for name, value in data["mods"]:
        lines.append(describe_mod(name, value))

    for name, value in data["grants"].items():
        if value is True:
            lines.append(grant_label(name))
        else:
            lines.append(f"+{value:g} {grant_label(name).lower()}")

    for event, effects in data["effects"].items():
        when = event.replace("_", " ")                 # "on_kill" -> "on kill"
        for effect in effects:
            lines.append(f"{describe_effect(effect)} ({when})")

    return lines

def register_skill_edge(a, b):
    adjacency.setdefault(a, []).append(b)
    adjacency.setdefault(b, []).append(a)

def neighbors(key):
    return adjacency.get(key, [])

def root_nodes():
    """Keys that are always active without costing a point."""
    return {k for k, d in skill_nodes.items() if d["is_root"]}

def node_is_on(key):
    """True if the node counts as active: allocated, or a free root."""
    return key in pending_nodes or skill_nodes[key]["is_root"]

def enter_tree():
    """Call when the panel opens: start editing from the committed state.
    Roots are filtered out — they are free and always active."""
    pending_nodes.clear()
    pending_nodes.update(k for k in allocated_nodes if k in skill_nodes and not skill_nodes[k]["is_root"])

def points_available(player):
    """Roots never enter pending_nodes, so they never cost a point."""
    earned = max(0, player.level - 1)
    return earned - len(pending_nodes)

def prereqs_met(key):
    """Connected to something that is on — an allocated node OR a root."""
    return any(node_is_on(n) for n in neighbors(key))

def can_allocate(player, key):
    if skill_nodes[key]["is_root"]:
        return False          # always on, nothing to click
    return key not in pending_nodes and prereqs_met(key) and points_available(player) > 0

def allocate(player, key):
    if not can_allocate(player, key):
        return False
    pending_nodes.add(key)
    return True

def can_deallocate(key):
    """A node can be unallocated only if every OTHER pending node still has
    a path back to a root without it — same rule as allocating, reversed."""
    if key not in pending_nodes:
        return False
    remaining = pending_nodes - {key}
    reached = set()
    frontier = list(root_nodes())
    while frontier:
        n = frontier.pop()
        for nb in neighbors(n):
            if nb in remaining and nb not in reached:
                reached.add(nb)
                frontier.append(nb)
    return reached == remaining

def deallocate(key):
    if not can_deallocate(key):
        return False
    pending_nodes.discard(key)
    return True

def pending_removed():
    return allocated_nodes - pending_nodes

def pending_respec_cost():
    return len(pending_removed()) * respec_cost_per_node

def has_pending_changes():
    return pending_nodes != allocated_nodes

def commit_changes(player):
    """Apply the staged edits. Returns False (and changes nothing) if the
    player can't afford the gold cost of whatever got unallocated."""
    cost = pending_respec_cost()
    if player.coins < cost:
        return False
    player.coins -= cost
    allocated_nodes.clear()
    allocated_nodes.update(pending_nodes)
    player.recalculate_stats(force=True)
    return True

def discard_changes():
    pending_nodes.clear()
    pending_nodes.update(allocated_nodes)

def reset_all(player):
    """Dev/testing tool — stays instant and free, bypasses the confirm flow entirely."""
    allocated_nodes.clear()
    pending_nodes.clear()
    player.recalculate_stats(force=True)