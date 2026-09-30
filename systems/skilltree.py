skill_nodes = {}
adjacency = {}
allocated_nodes = set()
pending_nodes = set()      # what's being edited while the tree panel is open

respec_cost_per_node = 25  # gold to unallocate one node

def register_skill_node(key, name, position, stats=None, is_root=False, sprite_name=None):
    skill_nodes[key] = {
        "name": name,
        "stats": stats or [],
        "position": position,
        "is_root": is_root,
        "sprite_name": sprite_name,
    }
    return key

def register_skill_edge(a, b):
    adjacency.setdefault(a, []).append(b)
    adjacency.setdefault(b, []).append(a)

def neighbors(key):
    return adjacency.get(key, [])

def enter_tree():
    """Call when the panel opens: start editing from the committed state."""
    pending_nodes.clear()
    pending_nodes.update(allocated_nodes)

def points_available(player):
    earned = max(0, player.level - 1)
    return earned - len(pending_nodes)

def prereqs_met(key):
    if skill_nodes[key]["is_root"]:
        return True
    return any(n in pending_nodes for n in neighbors(key))

def can_allocate(player, key):
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
    roots = {n for n in remaining if skill_nodes[n]["is_root"]}
    reached = set(roots)
    frontier = list(roots)
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