skill_nodes = {}      # key -> {"name", "stats", "position", "is_root", "sprite_name"}
adjacency = {}         # key -> [connected node keys]
allocated_nodes = set()

def register_skill_node(key, name, position, stats=None, is_root=False, sprite_name=None):
    skill_nodes[key] = {
        "name": name,
        "stats": stats or [],
        "position": position,        # (x, y) in skill-tree canvas pixels — see ui/skilltree.py
        "is_root": is_root,          # True = always allocatable (an entry point into the tree)
        "sprite_name": sprite_name,  # optional; falls back to a plain colored circle
    }
    return key

def register_skill_edge(a, b):
    """Connects two nodes both ways. Once either side is allocated, the other becomes allocatable."""
    adjacency.setdefault(a, []).append(b)
    adjacency.setdefault(b, []).append(a)

def neighbors(key):
    return adjacency.get(key, [])

def points_available(player):
    earned = max(0, player.level - 1)
    return earned - len(allocated_nodes)

def prereqs_met(key):
    if skill_nodes[key]["is_root"]:
        return True
    return any(n in allocated_nodes for n in neighbors(key))

def can_allocate(player, key):
    return key not in allocated_nodes and prereqs_met(key) and points_available(player) > 0

def allocate(player, key):
    if not can_allocate(player, key):
        return False
    allocated_nodes.add(key)
    player.recalculate_stats(force=True)
    return True

def reset_all(player):
    allocated_nodes.clear()
    player.recalculate_stats(force=True)