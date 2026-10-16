"""The passive skill tree screen. Everything is in ui/treepanel.py - this only
says which tree it shows and what the header says."""
from ui.treepanel import TreePanel

class SkillTreePanel(TreePanel):
    def toggle(self):
        if self.open:
            self.request_close()
        else:
            from systems.skilltree import passive_progress
            self.show(passive_progress, fit=False)       # keeps where you left the view

    def header_lines(self):
        return [(f"Skill Points: {self.progress.points_available()}", (255, 255, 255))]

skill_tree_panel = SkillTreePanel()
