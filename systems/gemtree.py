"""GEM AND PET TREES - every gem TYPE has a tree layout, every gem ITEM its own points.

They are normal trees from systems/trees.py: every node option is explained there.
What is special about them:

    - ISOLATED. Two Fireball gems use the same layout, but each item keeps its
      own points and sockets (item.tree). Nothing in a gem tree reaches the
      player or any other gem.
    - points come from the gem's level, which comes from kills: a new gem is
      level 1 with 10 points, +10 per level, 100 at level 10
    - SECTIONS: a gem tree can have sections (systems/trees.py). A section point
      comes at level 1 and at level 6, so 2 of 3 sections can be open at once
    - an ACTIVE GEM tree gives "mods" a single hit can use, and "effects"
      ("on_hit" / "on_kill") - they change only this gem's hits - and has
      sockets for support gems
    - a PET tree gives "mods" that are the pet's own stats - they change only this pet

Content (content/gem_trees.py, content/pets/...):

    tree = gem_tree("fireball")
    tree.node("start", "Ember Core", position=(0, 0), is_root=True)
    tree.node("dmg_1", "Kindling", position=(-200, -180), connects="start",
              mods=[("increased_damage", 12)])
    tree.node("socket_1", "Socket", position=(-400, 0), connects="start", is_socket=True)

    With sections, each section has its own root:
    tree.section("inferno", "Inferno")
    tree.node("inferno", "Inferno", position=(-900, 0), is_root=True, section="inferno")

    tree = pet_tree(pet_item_key("spider"))
    tree.node("venom", "Venom", position=(0, -200), connects="start",
              mods=[("increased_damage", 50)])
"""
from systems.trees import get_tree, TreeProgress

max_gem_level = 10
base_kills_for_level = 100      # kills from level 1 to 2. Every level after needs twice as many
points_per_gem_level = 5        # a new gem is level 1 with 10 points -> 100 points at level 10
section_point_levels = [1, 6]   # one section point at each of these levels
gem_respec_cost = 25            # gold to take back one saved point
section_lock_cost = 500         # gold to lock a section you had kept (to unlock a different one)

def gem_tree(template_key):
    """The tree layout for an active gem type. Its nodes give mods ONE hit can use
    (systems/mods.py) and effects ("on_hit" / "on_kill") - all for this gem only."""
    return get_tree(template_key, accepts={"mods", "effects"}, owner="gem",
                    respec_cost=gem_respec_cost, section_lock_cost=section_lock_cost)

def pet_tree(pet_key):
    """The tree layout for a pet type. Its nodes give the pet's own stats, with the
    same names as everywhere: ("increased_damage", 50), ("crit_chance", 5)."""
    return get_tree(pet_key, accepts={"mods"}, owner="pet",
                    respec_cost=gem_respec_cost, section_lock_cost=section_lock_cost)

def make_item_tree(item):
    """Every gem / pet ITEM gets its own progress - this is what keeps them apart."""
    return TreeProgress(item.template_key,
                        points_earned=lambda: item.gem_level() * points_per_gem_level,
                        section_points_earned=lambda: sum(1 for lv in section_point_levels if item.gem_level() >= lv))

def has_tree(item):
    tree = getattr(item, "tree", None)
    return tree is not None and bool(tree.tree.nodes)

# ---------------------------------------------------------------
# WHAT AN ITEM'S TREE GIVES - only ever used for that one item
# ---------------------------------------------------------------
def tree_supports(item):
    """The support gems in this item's sockets."""
    return [socketed.support_gem for socketed in item.tree.socketed() if hasattr(socketed, "support_gem")]

def tree_mods(item):
    """[(mod, value), ...] from this item's nodes. Only its own hits use them."""
    return list(item.tree.bonuses().get("mods", ()))

def tree_effects(item):
    """{"on_hit": [...], "on_kill": [...]} from this item's nodes. Only its own hits use them."""
    return dict(item.tree.bonuses().get("effects", {}))

def pet_stat_lines(bonuses):
    """A pet tree's mods as the pet's stat lines: ("increased_damage", 50) ->
    {"stat": "damage", "type": "increased", "amount": 50}."""
    from systems.mods import pet_stat_of
    lines = []
    for name, amount in bonuses.get("mods", ()):
        stat, kind = pet_stat_of(name)
        lines.append({"stat": stat, "type": kind, "amount": amount})
    return lines

def tree_stats(item):
    """[stat line, ...] from this item's nodes. Only its own pet uses them."""
    return pet_stat_lines(item.tree.bonuses())

def supports_gem(support_item, gem_item):
    """Can this support gem go in a socket of this active gem?"""
    from systems.abilities import active_gem_templates, ability_tags, ability_blocked
    from systems.supports import support_fits
    t = active_gem_templates.get(gem_item.template_key)
    if t is None:
        return False          # e.g. a pet: support gems don't fit it
    return support_fits(support_item.gem_type, ability_tags(t), ability_blocked(t))

# ---------------------------------------------------------------
# LEVELS FROM KILLS
# ---------------------------------------------------------------
def kills_for_level(level):
    """Kills from level-1 to `level`. Level 2 needs base_kills_for_level."""
    return base_kills_for_level * (2 ** (level - 2))

def level_from_kills(kills):
    """A new gem (0 kills) is level 1."""
    level = 1
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
    spent = sum(kills_for_level(l) for l in range(2, level + 1))
    return item.kills - spent

def kills_needed_for_next(item):
    level = item.gem_level()
    if level >= max_gem_level:
        return 0
    return kills_for_level(level + 1)

# ---------------------------------------------------------------
# The older way of writing nodes. Still works, so old content needs no changes.
#   support_type="pierce", value=2   ->   mods=[("pierce", 2)]
# ---------------------------------------------------------------
def is_pet_tree(template_key):
    from systems.pets import pet_configs, pet_item_key
    return any(pet_item_key(pet_type) == template_key for pet_type in pet_configs)

def register_gem_node(template_key, key, name, position, support_type=None, value=None, **options):
    if support_type is not None:
        from systems.supports import support_gem_types
        mod = support_gem_types[support_type]["mod"] or support_type
        options["mods"] = list(options.get("mods") or ()) + [(mod, value)]
    if options.get("stats"):                                  # old pet-tree stat lines -> mods
        options["mods"] = list(options.get("mods") or ()) + [
            (line["stat"] if line.get("type") == "flat" else "increased_" + line["stat"], line["amount"])
            for line in options.pop("stats")]
    tree = pet_tree(template_key) if is_pet_tree(template_key) else gem_tree(template_key)
    return tree.node(key, name, position, **options)

def register_gem_edge(template_key, a, b):
    get_tree(template_key).edge(a, b)
