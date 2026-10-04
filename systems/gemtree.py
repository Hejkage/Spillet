from systems.supports import SupportGem
from systems.rarity import rarity_common

gem_tree_nodes = {}
gem_tree_edges = {}

max_gem_level = 10
base_kills_for_level = 100
respec_cost_per_node = 25   # gold to unallocate one node

def register_gem_node(template_key, key, name, position, support_type=None, value=None, is_root=False, is_socket=False, sprite_name=None, stats=None):
    """stats = item-style stat lines, e.g. [{"stat": "buff_effect", "type": "increased", "amount": 100}].
    On a pet tree they change the pet's stats (systems/pets.py)."""
    gem_tree_nodes.setdefault(template_key, {})[key] = {
        "name": name,
        "position": position,
        "support_type": support_type,
        "value": value,
        "is_root": is_root,
        "is_socket": is_socket,
        "sprite_name": sprite_name,
        "stats": list(stats) if stats else [],
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

def enter_tree(item):
    """Call when the gem tree panel opens for this item."""
    item.pending_allocated = set(item.allocated)

def points_available(item):
    return item.gem_level() - len(item.pending_allocated)

def prereqs_met(item, key):
    template_key = item.template_key
    if nodes_for(item)[key]["is_root"]:
        return True
    return any(n in item.pending_allocated for n in neighbors(template_key, key))

def can_allocate(item, key):
    return key not in item.pending_allocated and prereqs_met(item, key) and points_available(item) > 0

def allocate(item, key):
    if not can_allocate(item, key):
        return False
    item.pending_allocated.add(key)
    return True

def can_deallocate(item, key):
    if key not in item.pending_allocated:
        return False
    nodes = nodes_for(item)
    if nodes[key].get("is_socket") and item.sockets.get(key) is not None:
        return False   # unsocket the support gem first
    remaining = item.pending_allocated - {key}
    roots = {n for n in remaining if nodes[n]["is_root"]}
    reached = set(roots)
    frontier = list(roots)
    template_key = item.template_key
    while frontier:
        n = frontier.pop()
        for nb in neighbors(template_key, n):
            if nb in remaining and nb not in reached:
                reached.add(nb)
                frontier.append(nb)
    return reached == remaining

def deallocate(item, key):
    if not can_deallocate(item, key):
        return False
    item.pending_allocated.discard(key)
    return True

def pending_removed(item):
    return item.allocated - item.pending_allocated

def pending_respec_cost(item):
    return len(pending_removed(item)) * respec_cost_per_node

def has_pending_changes(item):
    return item.pending_allocated != item.allocated

def commit_changes(item, player):
    cost = pending_respec_cost(item)
    if player.coins < cost:
        return False
    player.coins -= cost
    item.allocated = set(item.pending_allocated)
    player.gem_signature = None   # forces rebuild_gem_ability to pick up the change
    return True

def discard_changes(item):
    item.pending_allocated = set(item.allocated)

def reset_gem_tree(item):
    """Dev/testing tool — stays instant and free."""
    item.allocated.clear()
    item.pending_allocated.clear()

def tree_supports(item, allocated=None):
    if allocated is None:
        allocated = item.allocated
    supports = []
    nodes = nodes_for(item)
    for key in allocated:
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

def tree_stats(item, allocated=None):
    """Every stat line from the allocated nodes: [{"stat", "type", "amount"}, ...]."""
    if allocated is None:
        allocated = item.allocated
    nodes = nodes_for(item)
    return [mod for key in allocated if key in nodes for mod in nodes[key]["stats"]]

def supports_gem(support_item, gem_item):
    from systems.abilities import active_gem_templates
    from systems.supports import support_gem_types
    t = active_gem_templates.get(gem_item.template_key)
    if t is None:
        return False          # e.g. a pet: support gems don't fit it