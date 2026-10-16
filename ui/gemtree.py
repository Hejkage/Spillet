"""The gem / pet tree screen. Everything is in ui/treepanel.py - this only says
which item's tree it shows, what the header says, and what fits in a socket.

It always shows ONE item's own tree (item.tree), so two Fireballs never mix."""
from ui.treepanel import TreePanel

_WHITE = (255, 255, 255)
_GRAY = (200, 200, 200)

class GemTreePanel(TreePanel):
    def __init__(self):
        super().__init__()
        self.item = None

    def open_for(self, item):
        """Right click on a gem / pet. False if it has no tree."""
        from systems.gemtree import has_tree
        if not has_tree(item):
            return False
        from ui.panels import open_center_panel
        open_center_panel(None)
        self.item = item
        self.show(item.tree)
        return True

    def finish(self):
        super().finish()
        self.item = None

    def header_lines(self):
        from systems.gemtree import max_gem_level, kills_into_current_level, kills_needed_for_next
        item, progress = self.item, self.progress
        level = item.gem_level()
        lines = [(f"{item.name} - Level {level}/{max_gem_level}   Points: {progress.points_available()}", _WHITE)]
        if progress.tree.sections:
            lines.append((f"Section points: {progress.section_points_available()}", _WHITE))
        if level < max_gem_level:
            lines.append((f"Kills: {kills_into_current_level(item)} / {kills_needed_for_next(item)}", _GRAY))
        else:
            lines.append((f"Kills: {item.kills} (max level)", _GRAY))

        # everything the tree gives right now (with the points being edited)
        tree = progress.tree
        given = tree.describe(progress.bonuses(pending=True))
        given += [gem.describe() for gem in (s.support_gem for s in progress.socketed(pending=True))]
        if given:
            lines.append(("", _WHITE))
            lines.append(("This tree gives:", _WHITE))
            lines += [(text, _GRAY) for text in given]
        return lines

    def can_socket(self, held):
        from systems.items import gem_slot_support
        from systems.gemtree import supports_gem
        return getattr(held, "gem_slot", None) == gem_slot_support and supports_gem(held, self.item)

    def socket_lines(self, socketed):
        return [(socketed.support_gem.describe(), _GRAY)]

    def after_reset(self):
        from systems.player import player
        player.gem_signature = None

gem_tree_panel = GemTreePanel()
