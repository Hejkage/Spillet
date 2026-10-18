"""THE PASSIVE SKILL TREE - the player's big tree.

It is a normal tree from systems/trees.py: every node option is explained there.
This file only says what is special about the passive tree:

    - there is ONE, and the player owns it
    - points come from the player's level
    - what it gives counts for the player (collected in recalculate_stats)

Content goes in content/skilltree.py:

    passive_tree.node("vitality", "Vitality", position=(550, 600), connects="start",
        max_points=10, points_to_pass=5,
        per_point={"mods": [("max_health", 5)]},
        at_points={10: {"mods": [("increased_max_health", 10)]}})
"""
from systems.trees import get_tree, TreeProgress, node_kinds, register_node_kind   # noqa: F401 (content imports them from here)

points_per_level = 10      # skill points earned per level up

def passive_points_earned():
    from systems.player import player
    return max(0, player.level - 1) * points_per_level

passive_tree = get_tree("passive", respec_cost=5)          # respec_cost = gold per point taken back
passive_progress = TreeProgress("passive", passive_points_earned)

# Other files read these names, so they stay.
skill_nodes = passive_tree.nodes
adjacency = passive_tree.adjacency
allocated_points = passive_progress.saved                  # node key -> points (saved)

def allocated_sources():
    """-> [(node_key, bonuses), ...] for collect_bonuses() in the player."""
    return passive_progress.sources()

def load_points(saved, choices=None):
    passive_progress.load_points(saved, choices=choices)

# The older way of writing nodes. Still works, so content/skilltree.py needs no changes.
def register_skill_node(key, name, position, **options):
    return passive_tree.node(key, name, position, **options)

def register_skill_edge(a, b):
    passive_tree.edge(a, b)

# Kept here so content/skilltree.py can keep importing them from this file.
from systems.bonuses import register_grant_label, grant_label   # noqa: E402,F401
