"""TREES - every skill tree in the game is made with this ONE system.

    the passive tree      one tree, points from the player's level   (systems/skilltree.py)
    a gem / pet tree      one tree per gem TYPE ("fireball")         (systems/gemtree.py)

TWO THINGS, kept apart on purpose:

    Tree           the LAYOUT: nodes, lines, what each node gives. Made once, in content/.
    TreeProgress   ONE OWNER's points in a tree. The player has one for the passive
                   tree. Every gem ITEM has its own - so two Fireballs share the
                   layout, but never their points, sockets, sections or bonuses.

MAKING A TREE (in content/):

    tree = get_tree("passive")
    tree.node("start", "Origin", position=(0, 0), is_root=True)
    tree.node("vitality", "Vitality", position=(-25, -43), connects="start",
              max_points=10, points_to_pass=5,
              per_point={"mods": [("max_health", 5)]})

NODE OPTIONS - the same in every tree:

    kind            "small", "notable", "keystone"... its size and default points
    frame           border sprite. Left out = the kind's frame
    sprite_name     art drawn on top of the frame
    max_points      how many points it can take
    points_to_pass  points needed before the nodes next to it open up
    per_point       {part: ...} given for EVERY point
    at_points       {points: {part: ...}} given AT that many points. (1, 4) = points 1 to 4
    stats / mods / grants / effects / summons    shortcut: all given at the first point
    is_root         always on and free. Every path starts at a root
    is_socket       holds an item (a support gem in a gem tree)
    description     lore line at the bottom of the tooltip
    connects        a key, or a list of keys, this node has a line to
    one_way         True: the nodes in `connects` unlock THIS node, but this node
                    does not unlock them (like a WoW talent tree). Default: both ways.
                    For a single line: tree.edge("a", "b", one_way=True)  (a unlocks b)
    section         which section the node belongs to (see SECTIONS below)
    cost            skill points ONE rank of this node uses. Default 1.
                    cost=3: a keystone that takes 3 points to get.
    choices         a CHOICE node: pick one of these, like a WoW choice talent.
                    Each choice is a dict with "name" and the same bonus options as
                    a node (mods / stats / ... or per_point / at_points), plus
                    "sprite_name" if it has its own art:
                        choices=[{"name": "Volley", "mods": [("projectiles", 1)]},
                                 {"name": "Piercing", "mods": [("pierce", 1)]}]
                    The node is drawn split; click the half you want. Switching
                    a kept choice later costs the same gold as taking the points out.

The five parts (stats, mods, grants, effects, summons) are the same as on items:
see systems/bonuses.py.

SECTIONS - a tree can be split into parts that must be UNLOCKED with a section point:

    tree.section("inferno", "Inferno")
    tree.node("inferno_start", "Inferno", position=(-900, 0), is_root=True, section="inferno")
    tree.node("ember", "Ember", position=(-900, -200), connects="inferno_start", section="inferno", ...)

    A section's root is off until the section is unlocked. Where section points
    come from is the owner's business (TreeProgress section_points_earned).
    Emptying a section gives its section point back (locking a section you had
    saved costs tree.section_lock_cost gold).

WHAT A TREE ACCEPTS: get_tree("fireball", accepts={"mods"}). A node using any
other part is an error at start-up - so nothing is ever silently ignored.
OWNER: who the tree's mods are for (systems/mods.py):
    "player"  anything                      (the passive tree)
    "gem"     only mods ONE hit can use     (gem trees: crit, penetration, pierce...)
    "pet"     only the pet's own stats      (pet trees)
A mod that can't work for the owner is an error when the node is made.
"""
from systems.bonuses import bonus_parts, add_part, scale_part

# ---------------------------------------------------------------
# NODE KINDS - shared by every tree.
#   size            how big the node is at 100% zoom (tree pixels). Frame and
#                   art are scaled to this, so draw them at any size.
#   frame           border sprite. None/missing = a plain circle.
#   max_points      default for nodes that give something per point
#   points_to_pass  default points needed to move past it
# ---------------------------------------------------------------
node_kinds = {}

def register_node_kind(name, size, frame=None, max_points=10, points_to_pass=5):
    node_kinds[name] = {"size": size, "frame": frame,
                        "max_points": max_points, "points_to_pass": points_to_pass}

register_node_kind("small",    size=32, frame="node_small_frame",    max_points=10, points_to_pass=5)
register_node_kind("notable",  size=48, frame="node_notable_frame",  max_points=1,  points_to_pass=1)
register_node_kind("keystone", size=64, frame="node_keystone_frame", max_points=1,  points_to_pass=1)
register_node_kind("root",     size=48, frame="node_root_frame",     max_points=0,  points_to_pass=0)
register_node_kind("socket",   size=48, frame="node_socket_frame",   max_points=1,  points_to_pass=1)


def expand_points(at_points):
    """at_points keys can be one point (5) or a range ((1, 4) = points 1, 2, 3 and 4).
    Two entries for the same point are added together."""
    result = {}
    for key, bonus in (at_points or {}).items():
        points = range(key[0], key[1] + 1) if isinstance(key, tuple) else [key]
        for point in points:
            for part, value in bonus.items():
                add_part(result.setdefault(int(point), {}), part, value)
    return result


# ---------------------------------------------------------------
# THE LAYOUT
# ---------------------------------------------------------------
trees = {}

def get_tree(key, **settings):
    """The tree called `key`. Made the first time it is asked for.
    settings (any of them, any time): see Tree.settings()."""
    if key not in trees:
        trees[key] = Tree(key)
    trees[key].settings(**settings)
    return trees[key]

class Tree:
    def __init__(self, key):
        self.key = key
        self.nodes = {}           # node key -> node dict
        self.adjacency = {}       # node key -> [node keys it has a line to]   (for drawing)
        self.unlocks = {}         # node key -> [node keys it can unlock]      (for points)
        self.one_way = set()      # (a, b): the line from a to b is one-way
        self.sections = {}        # section key -> {"name": ...}
        self.accepts = set(bonus_parts)    # which of the five parts a node may give
        self.respec_cost = 5      # gold to take back ONE saved point
        self.section_lock_cost = 500       # gold to lock a section you had saved
        self.owner = "player"     # "player", "gem" or "pet": which mods make sense here

    @property
    def pet_stats(self):
        return self.owner == "pet"

    def settings(self, accepts=None, respec_cost=None, section_lock_cost=None, owner=None):
        if owner is not None:
            self.owner = owner
        if accepts is not None:
            self.accepts = set(accepts)
        if respec_cost is not None:
            self.respec_cost = respec_cost
        if section_lock_cost is not None:
            self.section_lock_cost = section_lock_cost

    # --- building it --------------------------------------------------------
    def section(self, key, name):
        """A part of the tree that needs a section point to unlock."""
        self.sections[key] = {"name": name}
        return key

    def node(self, key, name, position, kind="small", frame=None, sprite_name=None,
             max_points=None, points_to_pass=None, per_point=None, at_points=None,
             stats=None, mods=None, grants=None, effects=None, summons=None,
             is_root=False, is_socket=False, description=None, connects=None, one_way=False,
             section=None, cost=1, choices=None):
        """Add one node. See the top of this file for what each option does."""
        where = f"Tree '{self.key}', node '{key}'"
        if key in self.nodes:
            raise ValueError(f"{where}: made twice")
        if is_root:
            kind = "root" if kind == "small" else kind
        elif is_socket:
            kind = "socket" if kind == "small" else kind
        if kind not in node_kinds:
            raise ValueError(f"{where}: unknown kind '{kind}'. Kinds: {sorted(node_kinds)}")
        if section is not None and section not in self.sections:
            self.section(section, section.replace("_", " ").title())    # named after its key

        per_point, at_points = self._bonus_tables(where, per_point, at_points, stats, mods, grants, effects, summons)
        options = []
        for i, choice in enumerate(choices or ()):
            choice = dict(choice)
            c_name = choice.pop("name", f"Choice {i + 1}")
            c_sprite = choice.pop("sprite_name", None)
            c_per, c_at = self._bonus_tables(f"{where}, choice '{c_name}'", choice.pop("per_point", None),
                                             choice.pop("at_points", None), **choice)
            options.append({"name": c_name, "sprite_name": c_sprite, "per_point": c_per, "at_points": c_at})
        if choices is not None and len(options) < 2:
            raise ValueError(f"{where}: choices needs at least 2 options")

        config = node_kinds[kind]
        if is_root:
            max_points = 0
        if max_points is None:
            # per_point: the kind's default. Otherwise its highest at_points,
            # so a node never takes points that do nothing. A path-only node takes 1.
            tables = options or [{"per_point": per_point, "at_points": at_points}]
            if any(t["per_point"] for t in tables):
                max_points = config["max_points"]
            else:
                max_points = max((at for t in tables for at in t["at_points"]), default=1)
        if points_to_pass is None:
            points_to_pass = min(config["points_to_pass"], max_points)

        self.nodes[key] = {
            "name": name,
            "position": position,
            "kind": kind,
            "frame": frame or config["frame"],
            "sprite_name": sprite_name,
            "max_points": max_points,
            "points_to_pass": points_to_pass,
            "per_point": per_point or {},
            "at_points": at_points,
            "is_root": is_root,
            "is_socket": is_socket,
            "section": section,
            "cost": max(1, int(cost)),
            "choices": options,               # [] = a normal node
            "description": description or "",
        }
        for other in ([connects] if isinstance(connects, str) else connects or ()):
            self.edge(other, key, one_way=one_way)        # the earlier node leads to this one
        return key

    def _bonus_tables(self, where, per_point, at_points, stats=None, mods=None, grants=None,
                      effects=None, summons=None):
        """-> (per_point, at_points) from a node's (or a choice's) bonus options."""
        at_points = expand_points(at_points)
        first = {part: value for part, value in (("stats", stats), ("mods", mods), ("grants", grants),
                                                  ("effects", effects), ("summons", summons)) if value}
        if first:                                         # the shortcut: all on the first point
            merged = dict(at_points.get(1, {}))
            for part, value in first.items():
                add_part(merged, part, value)
            at_points[1] = merged
        used = set(per_point or {}) | {part for bonus in at_points.values() for part in bonus}
        if used - self.accepts:
            raise ValueError(f"{where}: this tree only takes {sorted(self.accepts)}, "
                             f"not {sorted(used - self.accepts)}")
        from systems.mods import owner_mod_problem
        mods = [name for name, _ in (per_point or {}).get("mods", ())]
        mods += [name for bonus in at_points.values() for name, _ in bonus.get("mods", ())]
        for name in mods:
            problem = owner_mod_problem(name, self.owner)
            if problem:
                raise ValueError(f"{where}: {problem}")
        return per_point or {}, at_points

    def edge(self, a, b, one_way=False):
        """A line between two nodes. one_way=True: a unlocks b, but b doesn't unlock a."""
        self.adjacency.setdefault(a, []).append(b)
        self.adjacency.setdefault(b, []).append(a)
        self.unlocks.setdefault(a, []).append(b)
        if one_way:
            self.one_way.add((a, b))
        else:
            self.unlocks.setdefault(b, []).append(a)

    # --- reading it ---------------------------------------------------------
    def neighbors(self, key):
        return self.adjacency.get(key, [])

    def unlocked_by(self, key):
        """The nodes that can open this one."""
        return [n for n in self.adjacency.get(key, ()) if key in self.unlocks.get(n, ())]

    def roots(self):
        return {k for k, d in self.nodes.items() if d["is_root"]}

    def section_of(self, key):
        return self.nodes[key]["section"]

    def section_nodes(self, section):
        return [k for k, d in self.nodes.items() if d["section"] == section]

    def section_root(self, section):
        return next((k for k in self.section_nodes(section) if self.nodes[k]["is_root"]), None)

    def size(self, key):
        return node_kinds[self.nodes[key]["kind"]]["size"]

    def bonus_table(self, key, choice=None):
        """Where a node's bonuses live: the node itself, or the picked choice."""
        data = self.nodes[key]
        if data["choices"]:
            return data["choices"][choice or 0]
        return data

    def node_bonuses(self, key, points, choice=None):
        """{part: ...} - everything the node gives with this many points."""
        data = self.bonus_table(key, choice)
        total = {}
        if points <= 0:
            return total
        for part, value in data["per_point"].items():
            add_part(total, part, scale_part(part, value, points))
        for at, bonus in sorted(data["at_points"].items()):
            if at <= points:
                for part, value in bonus.items():
                    add_part(total, part, value)
        return total

    def point_bonus(self, key, point, choice=None):
        """{part: ...} - what point number `point` adds on its own."""
        data = self.bonus_table(key, choice)
        total = {}
        for part, value in data["per_point"].items():
            add_part(total, part, scale_part(part, value, 1))
        for part, value in data["at_points"].get(point, {}).items():
            add_part(total, part, value)
        return total

    def describe(self, bonuses):
        """-> [str, ...] the tooltip lines for a {part: ...} total."""
        from systems.bonuses import describe_bonuses
        if not self.pet_stats:
            return describe_bonuses(bonuses)
        from systems.pets import describe_pet_mod
        from systems.gemtree import pet_stat_lines
        return [describe_pet_mod(line) for line in pet_stat_lines(bonuses)]


# ---------------------------------------------------------------
# ONE OWNER'S POINTS IN A TREE
# ---------------------------------------------------------------
class TreeProgress:
    """saved / pending           node -> points
    saved_sections / pending_sections   the unlocked sections
        saved = what COUNTS (bonuses, sockets). pending = what the tree screen
        edits; copied into saved on "Keep changes", thrown away on "Discard".
    sockets  socket node -> the item in it (or None). Changes at once.
    points_earned()            how many points the owner has in total
    section_points_earned()    how many sections the owner may unlock"""

    def __init__(self, tree_key, points_earned, section_points_earned=None):
        self.tree_key = tree_key
        self.points_earned = points_earned
        self.section_points_earned = section_points_earned or (lambda: 0)
        self.saved = {}
        self.pending = {}
        self.saved_sections = set()
        self.pending_sections = set()
        self.saved_choices = {}           # choice node -> index of the picked choice
        self.pending_choices = {}
        self.sockets = {}

    @property
    def tree(self):
        return get_tree(self.tree_key)

    # --- sections -----------------------------------------------------------
    def section_open(self, section, pending=True):
        """True if a node in this section may be used. No section = always open."""
        if section is None:
            return True
        return section in (self.pending_sections if pending else self.saved_sections)

    def node_open(self, key, pending=True):
        return self.section_open(self.tree.section_of(key), pending)

    def active_roots(self, pending=True):
        return {k for k in self.tree.roots() if self.node_open(k, pending)}

    def section_points_available(self):
        return self.section_points_earned() - len(self.pending_sections)

    def section_points_in(self, section):
        return sum(self.pending.get(k, 0) for k in self.tree.section_nodes(section))

    def can_unlock_section(self, section):
        return (section in self.tree.sections and section not in self.pending_sections
                and self.section_points_available() > 0)

    def unlock_section(self, section):
        if not self.can_unlock_section(section):
            return False
        self.pending_sections.add(section)
        return True

    def can_lock_section(self, section):
        """Only an EMPTY section can be locked again (its section point comes back)."""
        return section in self.pending_sections and self.section_points_in(section) == 0

    def lock_section(self, section):
        if not self.can_lock_section(section):
            return False
        self.pending_sections.discard(section)
        return True

    # --- what counts --------------------------------------------------------
    def node_points(self, pending=False):
        """node -> points: real nodes with points, in an open section (a root never holds points)."""
        points = self.pending if pending else self.saved
        nodes = self.tree.nodes
        return {k: p for k, p in points.items()
                if k in nodes and p > 0 and not nodes[k]["is_root"] and self.node_open(k, pending)}

    def choice_of(self, key, pending=True):
        """The picked choice of a choice node (None = nothing picked yet)."""
        return (self.pending_choices if pending else self.saved_choices).get(key)

    def cost_of(self, key):
        return self.tree.nodes[key]["cost"]

    def sources(self, pending=False):
        """[(node_key, {part: ...}), ...] - one per node with points."""
        tree = self.tree
        return [(key, tree.node_bonuses(key, p, self.choice_of(key, pending)))
                for key, p in self.node_points(pending).items()]

    def bonuses(self, pending=False):
        """Everything the nodes with points give, added together: {part: ...}"""
        total = {}
        for _, bonus in self.sources(pending):
            for part, value in bonus.items():
                add_part(total, part, value)
        return total

    def socketed(self, pending=False):
        """The items in sockets that have a point."""
        on = self.node_points(pending)
        return [item for key, item in self.sockets.items() if item is not None and key in on]

    # --- editing (the tree screen works on `pending`) ----------------------
    def start_edit(self):
        """Call when the tree screen opens."""
        self.pending = self.node_points()
        self.pending_sections = set(self.saved_sections)
        self.pending_choices = {k: c for k, c in self.saved_choices.items() if k in self.pending}

    def points_in(self, key):
        return self.pending.get(key, 0)

    def node_is_on(self, key):
        return self.points_in(key) > 0 or key in self.active_roots()

    def is_passable(self, key, points=None):
        """True if the nodes this one unlocks may get points."""
        data = self.tree.nodes[key]
        if data["is_root"]:
            return self.node_open(key)
        have = self.points_in(key) if points is None else points
        return have > 0 and have >= data["points_to_pass"]

    def points_spent(self):
        return sum(p * self.cost_of(k) for k, p in self.pending.items() if k in self.tree.nodes)

    def points_available(self):
        return self.points_earned() - self.points_spent()

    def can_allocate(self, key):
        """Can ONE more point go into this node?"""
        data = self.tree.nodes[key]
        if data["is_root"] or self.points_in(key) >= data["max_points"]:
            return False
        if self.points_available() < data["cost"] or not self.node_open(key):
            return False
        return self.points_in(key) > 0 or any(self.is_passable(n) for n in self.tree.unlocked_by(key))

    def allocate(self, key, choice=None):
        """One more point. On a choice node, `choice` picks which option
        (on a node that already has points, a different `choice` SWITCHES to it)."""
        data = self.tree.nodes[key]
        if data["choices"] and choice is not None and self.points_in(key) > 0 \
                and choice != self.choice_of(key):
            self.pending_choices[key] = choice           # switch, no extra point
            return True
        if not self.can_allocate(key):
            return False
        if data["choices"] and self.points_in(key) == 0:
            self.pending_choices[key] = choice or 0
        self.pending[key] = self.points_in(key) + 1
        return True

    def allocate_all(self, key, choice=None):
        """As many points as the node takes (or you have). Returns how many went in."""
        added = 0
        if self.allocate(key, choice):
            added += 1
        while self.allocate(key):
            added += 1
        return added

    def _all_connected(self, points):
        """True if every node with points can still be reached from an open root,
        following lines the way they unlock, through passable nodes."""
        tree = self.tree
        reached = set(self.active_roots())
        frontier = list(reached)
        while frontier:
            n = frontier.pop()
            have = points.get(n, 0)
            if not (tree.nodes[n]["is_root"] or (have > 0 and have >= tree.nodes[n]["points_to_pass"])):
                continue                                  # not passable: the path stops here
            for nb in tree.unlocks.get(n, ()):
                if nb not in reached and points.get(nb, 0) > 0:
                    reached.add(nb)
                    frontier.append(nb)
        return all(k in reached for k, p in points.items() if p > 0)

    def can_deallocate(self, key):
        """Can ONE point come out without cutting anything off?"""
        if self.points_in(key) <= 0:
            return False
        if self.points_in(key) == 1 and self.sockets.get(key) is not None:
            return False                                  # take the gem out first
        after = dict(self.pending)
        after[key] -= 1
        return self._all_connected(after)

    def deallocate(self, key):
        if not self.can_deallocate(key):
            return False
        self.pending[key] -= 1
        if self.pending[key] <= 0:
            del self.pending[key]
            self.pending_choices.pop(key, None)          # empty again: nothing picked
        return True

    def deallocate_all(self, key):
        removed = 0
        while self.deallocate(key):
            removed += 1
        return removed

    # --- keeping or throwing away the edit ----------------------------------
    def points_removed(self):
        """Saved skill points the edit takes out (those cost gold). Switching a
        kept choice counts as taking that node's points out."""
        removed = 0
        for k, p in self.saved.items():
            if k not in self.tree.nodes:
                continue
            if k in self.pending and self.choice_of(k) != self.choice_of(k, pending=False):
                gone = p                                  # switched to another choice
            else:
                gone = max(0, p - self.pending.get(k, 0))
            removed += gone * self.cost_of(k)
        return removed

    def sections_locked(self):
        """Saved sections the edit locks again (those cost extra)."""
        return self.saved_sections - self.pending_sections

    def respec_cost(self):
        """Gold to keep the edit. Change THIS to make locking a section cost a
        special currency later."""
        tree = self.tree
        return self.points_removed() * tree.respec_cost + len(self.sections_locked()) * tree.section_lock_cost

    def has_changes(self):
        return (self.pending != self.node_points() or self.pending_sections != self.saved_sections
                or self.pending_choices != {k: c for k, c in self.saved_choices.items() if k in self.saved})

    def commit(self, player):
        """Keep the edit. False (and nothing changes) if the gold isn't there."""
        cost = self.respec_cost()
        if player.coins < cost:
            return False
        player.coins -= cost
        self.saved.clear()                               # in place: other code holds this dict
        self.saved.update(self.pending)
        self.saved_sections = set(self.pending_sections)
        self.saved_choices = {k: c for k, c in self.pending_choices.items() if k in self.saved}
        refresh_owner(player)
        return True

    def discard(self):
        self.start_edit()

    def reset(self, player):
        """Dev/testing tool: every point and section out, free and instant."""
        self.saved.clear()
        self.pending = {}
        self.saved_sections = set()
        self.pending_sections = set()
        self.saved_choices = {}
        self.pending_choices = {}
        refresh_owner(player)

    # --- the save file ------------------------------------------------------
    def points_to_save(self):
        return dict(self.node_points())

    def sections_to_save(self):
        return sorted(self.saved_sections)

    def choices_to_save(self):
        return {k: c for k, c in self.saved_choices.items() if k in self.saved}

    def load_points(self, saved, sections=(), choices=None):
        """Old saves (a list of node keys) give each node 1 point.
        Roots, nodes that no longer exist and nodes in locked sections are dropped."""
        if not isinstance(saved, dict):
            saved = {k: 1 for k in saved or ()}
        self.saved_sections = {s for s in sections or () if s in self.tree.sections}
        self.saved.clear()
        self.saved.update({k: int(p) for k, p in saved.items()})
        clean = self.node_points()
        self.saved.clear()                               # in place: other code holds this dict
        self.saved.update(clean)
        nodes = self.tree.nodes
        self.saved_choices = {k: int(c) for k, c in (choices or {}).items()
                              if k in self.saved and 0 <= int(c) < len(nodes[k]["choices"])}
        for k in self.saved:                             # a node that became a choice node
            if nodes[k]["choices"] and k not in self.saved_choices:
                self.saved_choices[k] = 0
        self.start_edit()


def refresh_owner(player):
    """After points changed: the player's stats, pets and gem abilities are worked out again."""
    player.gem_signature = None                  # gem abilities rebuild with the new tree
    player.recalculate_stats(force=True)         # the passive tree, and every pet's stats
