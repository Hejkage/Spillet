"""THE PASSIVE SKILL TREE - nodes that take POINTS.

A node can take one point (a notable) or many (max_points=10). What each point
gives is set with two things, and you can use either or both:

    per_point   given for EVERY point:      +5 health per point
    at_points   given AT a number of points: {10: +10% increased health}

    register_skill_node("vitality", "Vitality", position=(550, 600),
        max_points=10, points_to_pass=5,
        per_point={"stats": [{"stat": "max_health", "type": "flat", "amount": 5}]},
        at_points={10: {"stats": [{"stat": "max_health", "type": "increased", "amount": 10}]}})

A node with ten different things at ten points: no per_point, at_points 1-10.
Both use the same five parts as items (systems/bonuses.py):
stats, mods, grants, effects, summons.

points_to_pass = how many points it needs before the nodes next to it open up.

The old way - stats=[...], mods=[...] directly on the node - still works: that
is a node whose FIRST point gives it all.

Removing points never breaks a path: a node can't go below points_to_pass while
something further along only connects through it.
"""

skill_nodes = {}
adjacency = {}
allocated_points = {}     # node key -> points (saved)
pending_points = {}       # what's being edited while the tree panel is open

points_per_level = 10     # skill points earned per level up
respec_cost_per_point = 5 # gold to take back ONE point that was already saved


# ---------------------------------------------------------------
# NODE KINDS - how a node looks, and its default point numbers.
#   size            in sprite pixels. Draw the frame sprite at exactly this size.
#   frame           sprite drawn behind the node's own icon. None/missing = a circle.
#   max_points      default for nodes that give something per point
#   points_to_pass  default points needed to move past it
# A node picks one with kind="notable". New kinds: register_node_kind() in content/.
# ---------------------------------------------------------------
node_kinds = {}

def register_node_kind(name, size, frame=None, max_points=10, points_to_pass=5):
    node_kinds[name] = {"size": size, "frame": frame,
                        "max_points": max_points, "points_to_pass": points_to_pass}

register_node_kind("small",    size=32, frame="node_small_frame",    max_points=10, points_to_pass=5)
register_node_kind("notable",  size=48, frame="node_notable_frame",  max_points=1,  points_to_pass=1)
register_node_kind("keystone", size=64, frame="node_keystone_frame", max_points=1,  points_to_pass=1)
register_node_kind("root",     size=48, frame="node_root_frame",     max_points=0,  points_to_pass=0)


def register_skill_node(key, name, position, kind="small", max_points=None, points_to_pass=None,
                        per_point=None, at_points=None,
                        stats=None, mods=None, grants=None, effects=None, summons=None,
                        description=None, is_root=False, sprite_name=None):
    """position     where it sits, in tree pixels. Any numbers - the view fits itself.
    kind         "small", "notable", "keystone"... (register_node_kind)
    max_points   how many points it can take
    per_point    {part: ...} given for every point
    at_points    {points: {part: ...}} given when it reaches that many points
    stats/mods/grants/effects/summons   shortcut: all given at the first point
    description  a lore / quote line, shown at the bottom of the tooltip
    sprite_name  the icon drawn inside the frame (draw it at the size you want it)

    Left out, max_points is the kind's default if the node has per_point,
    otherwise its highest at_points - so a node never takes points that do nothing."""
    if kind not in node_kinds:
        raise ValueError(f"Skill node '{key}': unknown kind '{kind}'. Kinds: {sorted(node_kinds)}")
    at_points = {int(k): dict(v) for k, v in (at_points or {}).items()}
    first = {part: value for part, value in (("stats", stats), ("mods", mods), ("grants", grants),
                                              ("effects", effects), ("summons", summons)) if value}
    if first:                                      # the old way: everything on the first point
        merged = dict(at_points.get(1, {}))
        merged.update(first)
        at_points[1] = merged
    if is_root:
        kind = "root" if kind == "small" else kind
        max_points = 0
    config = node_kinds[kind]
    if max_points is None:
        max_points = config["max_points"] if per_point else max(at_points, default=0)
    if points_to_pass is None:
        points_to_pass = min(config["points_to_pass"], max_points)
    skill_nodes[key] = {
        "name": name,
        "position": position,
        "kind": kind,
        "max_points": max_points,
        "points_to_pass": points_to_pass,
        "per_point": per_point or {},
        "at_points": at_points,
        "description": description or "",
        "is_root": is_root,
        "sprite_name": sprite_name,
    }
    return key

def register_skill_edge(a, b):
    adjacency.setdefault(a, []).append(b)
    adjacency.setdefault(b, []).append(a)

def neighbors(key):
    return adjacency.get(key, [])

def root_nodes():
    """Keys that are always active without costing a point."""
    return {k for k, d in skill_nodes.items() if d["is_root"]}


# ---------------------------------------------------------------
# WHAT A NODE GIVES AT N POINTS
# ---------------------------------------------------------------
def _scaled(part, value, times):
    """One per_point part, given `times` times."""
    if part == "stats":
        return [dict(line, amount=line.get("amount", 0) * times) for line in value]
    if part == "mods":
        return [mod for mod in value for _ in range(times)]          # each point is its own copy
    if part == "grants":
        return {k: (v if v is True else v * times) for k, v in value.items()}
    if part == "summons":
        return {k: v * times for k, v in value.items()}
    if part == "effects":
        return {event: [e for e in effects for _ in range(times)] for event, effects in value.items()}
    return value

def _add(total, part, value):
    if part in ("stats", "mods"):
        total.setdefault(part, []).extend(value)
    elif part == "effects":
        for event, effects in value.items():
            total.setdefault(part, {}).setdefault(event, []).extend(effects)
    else:                                                            # grants / summons add up
        bucket = total.setdefault(part, {})
        for k, v in value.items():
            bucket[k] = True if v is True else bucket.get(k, 0) + v

def node_bonuses(key, points):
    """{part: ...} - everything the node gives with this many points."""
    data = skill_nodes[key]
    total = {}
    if points <= 0:
        return total
    for part, value in data["per_point"].items():
        _add(total, part, _scaled(part, value, points))
    for at, bonus in sorted(data["at_points"].items()):
        if at <= points:
            for part, value in bonus.items():
                _add(total, part, value)
    return total

def point_bonus(key, point):
    """{part: ...} - what point number `point` adds on its own."""
    data = skill_nodes[key]
    total = {}
    for part, value in data["per_point"].items():
        _add(total, part, _scaled(part, value, 1))
    for part, value in data["at_points"].get(point, {}).items():
        _add(total, part, value)
    return total

# What the allocated nodes add up to is collected by the player, together with
# the equipped items, in recalculate_stats() (see systems/bonuses.py).
def allocated_sources():
    """-> [(node_key, bonuses), ...] for collect_bonuses()."""
    return [(key, node_bonuses(key, points)) for key, points in allocated_points.items()
            if key in skill_nodes and points > 0]

# Kept here so content/skilltree.py can keep importing them from this file.
from systems.bonuses import register_grant_label, grant_label

def node_lines(key, points=None):
    """-> [str, ...] what the node gives with `points` points (default: its pending points)."""
    from systems.bonuses import describe_bonuses
    if points is None:
        points = pending_points.get(key, 0)
    return describe_bonuses(node_bonuses(key, points))


# ---------------------------------------------------------------
# POINTS
# ---------------------------------------------------------------
def points_in(key):
    return pending_points.get(key, 0)

def node_is_on(key):
    """True if the node counts as active: it has points, or it is a free root."""
    return points_in(key) > 0 or skill_nodes[key]["is_root"]

def is_passable(key, points=None):
    """True if the nodes next to this one may be allocated."""
    data = skill_nodes[key]
    if data["is_root"]:
        return True
    have = points_in(key) if points is None else points
    return have > 0 and have >= data["points_to_pass"]

def enter_tree():
    """Call when the panel opens: start editing from the saved state."""
    pending_points.clear()
    pending_points.update({k: p for k, p in allocated_points.items()
                           if k in skill_nodes and not skill_nodes[k]["is_root"] and p > 0})

def points_earned(player):
    return max(0, player.level - 1) * points_per_level

def points_available(player):
    return points_earned(player) - sum(pending_points.values())

def can_allocate(player, key):
    """Can ONE more point go into this node?"""
    data = skill_nodes[key]
    if data["is_root"] or points_in(key) >= data["max_points"]:
        return False
    if points_available(player) <= 0:
        return False
    return points_in(key) > 0 or any(is_passable(n) for n in neighbors(key))

def allocate(player, key):
    if not can_allocate(player, key):
        return False
    pending_points[key] = points_in(key) + 1
    return True

def allocate_all(player, key):
    """As many points as the node takes (or you have). Returns how many went in."""
    added = 0
    while allocate(player, key):
        added += 1
    return added

def _all_connected(points):
    """True if every node with points can still reach a root through passable nodes."""
    reached = set(root_nodes())
    frontier = list(reached)
    while frontier:
        n = frontier.pop()
        if not (skill_nodes[n]["is_root"] or (points.get(n, 0) > 0 and points.get(n, 0) >= skill_nodes[n]["points_to_pass"])):
            continue                                    # not passable: the path stops here
        for nb in neighbors(n):
            if nb not in reached and points.get(nb, 0) > 0:
                reached.add(nb)
                frontier.append(nb)
    return all(k in reached for k, p in points.items() if p > 0)

def can_deallocate(key):
    """Can ONE point come out without cutting anything off?"""
    if points_in(key) <= 0:
        return False
    after = dict(pending_points)
    after[key] -= 1
    return _all_connected(after)

def deallocate(key):
    if not can_deallocate(key):
        return False
    pending_points[key] -= 1
    if pending_points[key] <= 0:
        del pending_points[key]
    return True

def deallocate_all(key):
    """As many points as can come out without breaking a path. Returns how many."""
    removed = 0
    while deallocate(key):
        removed += 1
    return removed

def points_removed():
    """Saved points that the pending edit takes out (those cost gold)."""
    return sum(max(0, p - pending_points.get(k, 0)) for k, p in allocated_points.items())

def pending_respec_cost():
    return points_removed() * respec_cost_per_point

def has_pending_changes():
    saved = {k: p for k, p in allocated_points.items() if p > 0}
    return pending_points != saved

def commit_changes(player):
    """Apply the staged edits. Returns False (and changes nothing) if the
    player can't afford the gold cost of the points taken out."""
    cost = pending_respec_cost()
    if player.coins < cost:
        return False
    player.coins -= cost
    allocated_points.clear()
    allocated_points.update(pending_points)
    player.recalculate_stats(force=True)
    return True

def discard_changes():
    pending_points.clear()
    pending_points.update(allocated_points)

def reset_all(player):
    """Dev/testing tool - instant and free, bypasses the confirm flow entirely."""
    allocated_points.clear()
    pending_points.clear()
    player.recalculate_stats(force=True)

def load_points(saved):
    """From the save file. Old saves (a list of node keys) give each node 1 point."""
    allocated_points.clear()
    if isinstance(saved, dict):
        allocated_points.update({k: int(p) for k, p in saved.items() if k in skill_nodes})
    else:
        allocated_points.update({k: 1 for k in saved if k in skill_nodes})
