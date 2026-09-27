from systems.supports import SupportGem
from systems.rarity import rarity_common

gem_tree_nodes = {}   # template_key -> {node_key: data}
gem_tree_edges = {}   # template_key -> {node_key: [connected node keys]}

max_gem_level = 10
base_kills_for_level = 100

def register_gem_node(template_key, key, name, position, support_type=None, value=None, is_root=False, is_socket=False, sprite_name=None):
    gem_tree_nodes.setdefault(template_key, {})[key] = {
        "name": name,
        "position": position,
        "support_type": support_type,
        "value": value,
        "is_root": is_root,
        "is_socket": is_socket,
        "sprite_name": sprite_name,
    }
    return key

def register_gem_edge(template_key, a, b):
    edges = gem_tree_edges.setdefault(template_key, {})
    edges.setdefault(a, []).append(b)
    edges.setdefault(b, []).append(a)

def nodes_for(item):
    return gem_tree_nodes.get(getattr(item, "template_key", None), {})

def neighbors(template_key, key):
    return gem_tree_edges.get(template_key, {}).get(key, [])

def kills_for_level(level):
    """Hvad DET level koster: level 1 = 100, level 2 = 200, level 3 = 400..."""
    return base_kills_for_level * (2 ** (level - 1))

def level_from_kills(kills):
    level = 0
    spent = 0
    while level < max_gem_level:
        need = spent + kills_for_level(level + 1)
        if kills < need:
            break
        spent = need
        level += 1
    return level

def kills_into_current_level(item):
    level = item.gem_level()
    spent = sum(kills_for_level(l) for l in range(1, level + 1))
    return item.kills - spent

def kills_needed_for_next(item):
    level = item.gem_level()
    if level >= max_gem_level:
        return 0
    return kills_for_level(level + 1)

def points_available(item):
    return item.gem_level() - len(item.allocated)

def prereqs_met(item, key):
    template_key = item.template_key
    if nodes_for(item)[key]["is_root"]:
        return True
    return any(n in item.allocated for n in neighbors(template_key, key))

def can_allocate(item, key):
    return key not in item.allocated and prereqs_met(item, key) and points_available(item) > 0

def allocate(item, key):
    if not can_allocate(item, key):
        return False
    item.allocated.add(key)
    return True

def reset_gem_tree(item):
    item.allocated.clear()

def tree_supports(item):
    supports = []
    nodes = nodes_for(item)
    for key in item.allocated:
        data = nodes.get(key)
        if not data:
            continue
        if data.get("is_socket"):
            socketed = item.sockets.get(key)
            if socketed is not None:
                supports.append(socketed.support_gem)
        elif data["support_type"]:
            gem = SupportGem(data["support_type"], data["value"], rarity_common)
            gem.from_tree = True
            gem.node_name = data["name"]
            supports.append(gem)
    return supports