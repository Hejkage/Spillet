import pygame
from core.state import app
from core.screen import get_font
from systems.skilltree import (skill_nodes, adjacency, node_kinds, points_in, can_allocate, allocate, allocate_all,
                               can_deallocate, deallocate, deallocate_all, reset_all, points_available, enter_tree,
                               has_pending_changes, pending_respec_cost, commit_changes, discard_changes,
                               respec_cost_per_point, node_is_on, is_passable, node_bonuses, point_bonus)
from systems.player import player
from systems.items import draw_tooltip_box
from ui.treeview import TreeView

_WHITE = (255, 255, 255)
_GRAY = (200, 200, 200)

# --- colours ------------------------------------------------------------------
node_color_on        = (240, 200, 60)    # has points
node_color_full      = (255, 235, 140)   # all points in
node_color_available = (140, 140, 255)   # a point can go in
node_color_locked    = (70, 70, 75)
edge_color_on        = (120, 200, 120)
edge_color_off       = (80, 80, 90)
node_flavour_color   = (200, 160, 90)    # the lore / quote line at the bottom of a node tooltip
labels_from_zoom     = 1                 # node names are shown from this zoom and up

help_text = "Left click: add point   Right click: remove   Ctrl: all at once   Drag / WASD: move   Wheel: zoom"

class SkillTreePanel:
    def __init__(self):
        self.open = False
        self.view = TreeView()
        self.node_spots = {}             # key -> (x, y, radius) on screen, from the last draw
        self.reset_rect = None
        self.confirm_open = False
        self.confirm_keep_rect = None
        self.confirm_discard_rect = None

    def toggle(self):
        if self.open:
            self.request_close()
        else:
            enter_tree()
            if not self.view.fitted:                         # the first time: show the whole tree
                self.view.fit(d["position"] for d in skill_nodes.values())
            self.open = True

    def request_close(self):
        if has_pending_changes():
            self.confirm_open = True
        else:
            self.open = False

    def node_at(self, pos):
        for key, (x, y, radius) in self.node_spots.items():
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= radius ** 2:
                return key
        return None

    # --- drawing ------------------------------------------------------------
    def draw(self):
        if not self.open:
            return

        from systems.items import hover_state
        hover_state.item = None
        hover_state.ability = None
        hover_state.ground_item = None
        if not self.confirm_open:
            self.view.update()

        overlay = pygame.Surface((app.screen_width, app.screen_height), pygame.SRCALPHA)
        overlay.fill((10, 10, 15, 235))
        app.screen.blit(overlay, (0, 0))

        view = self.view
        zoom = view.zoom
        font = get_font(max(16, int(22 * app.ui_scale)))
        small_font = get_font(max(12, int(16 * app.ui_scale)))

        # --- edges ---
        drawn_edges = set()
        for key, neighbor_keys in adjacency.items():
            for other in neighbor_keys:
                edge = tuple(sorted((key, other)))
                if edge in drawn_edges or key not in skill_nodes or other not in skill_nodes:
                    continue
                drawn_edges.add(edge)
                lit = (node_is_on(key) and node_is_on(other)
                       and (is_passable(key) or is_passable(other)))
                pygame.draw.line(app.screen, edge_color_on if lit else edge_color_off,
                                 view.to_screen(*skill_nodes[key]["position"]),
                                 view.to_screen(*skill_nodes[other]["position"]), max(2, int(4 * zoom)))

        # --- nodes ---
        self.node_spots = {}
        for key, data in skill_nodes.items():
            x, y = view.to_screen(*data["position"])
            kind = node_kinds[data["kind"]]
            radius = max(3, int(kind["size"] * zoom / 2))
            if x < -radius or y < -radius or x > app.screen_width + radius or y > app.screen_height + radius:
                continue                                      # off screen
            self.node_spots[key] = (x, y, radius)
            points = points_in(key)
            if node_is_on(key):
                color = node_color_full if (points >= data["max_points"] and not data["is_root"]) else node_color_on
            elif can_allocate(player, key):
                color = node_color_available
            else:
                color = node_color_locked

            pygame.draw.circle(app.screen, color, (x, y), radius)
            frame = view.sprite(kind["frame"]) if kind["frame"] else None
            if frame:
                app.screen.blit(frame, frame.get_rect(center=(x, y)))
            else:
                pygame.draw.circle(app.screen, _WHITE, (x, y), radius, max(1, int(2 * zoom)))
            icon = view.sprite(data["sprite_name"]) if data["sprite_name"] else None
            if icon:
                app.screen.blit(icon, icon.get_rect(center=(x, y)))

            text_y = y + radius + 2
            if data["max_points"] > 1:
                counter = small_font.render(f"{points}/{data['max_points']}", True, _WHITE)
                app.screen.blit(counter, counter.get_rect(midtop=(x, text_y)))
                text_y += counter.get_height()
            if zoom >= labels_from_zoom:
                label = small_font.render(data["name"], True, _GRAY)
                app.screen.blit(label, label.get_rect(midtop=(x, text_y)))

        # --- header, help and buttons ---
        title = font.render(f"Skill Points: {points_available(player)}", True, _WHITE)
        app.screen.blit(title, (40, 30))
        hint = small_font.render(help_text, True, (160, 160, 170))
        app.screen.blit(hint, (40, 30 + title.get_height() + 4))

        btn_w, btn_h = 200, 50
        self.reset_rect = pygame.Rect(app.screen_width - btn_w - 40, app.screen_height - btn_h - 40, btn_w, btn_h)
        pygame.draw.rect(app.screen, (120, 40, 40), self.reset_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.reset_rect, width=2, border_radius=8)
        reset_label = font.render("Reset All", True, _WHITE)
        app.screen.blit(reset_label, reset_label.get_rect(center=self.reset_rect.center))

        hovered_key = self.node_at(pygame.mouse.get_pos())
        if hovered_key and not self.confirm_open and not view.dragging:
            self.draw_node_tooltip(hovered_key)

        if self.confirm_open:
            self.draw_confirm_prompt()

    def draw_confirm_prompt(self):
        font = get_font(max(16, int(22 * app.ui_scale)))
        cost = pending_respec_cost()
        message = f"Keep these changes? It will cost you {cost} gold." if cost > 0 else "Keep these changes?"

        box_w, box_h = 540, 160
        box_x = app.screen_width // 2 - box_w // 2
        box_y = app.screen_height // 2 - box_h // 2
        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box.fill((20, 20, 25, 245))
        app.screen.blit(box, (box_x, box_y))
        pygame.draw.rect(app.screen, (220, 220, 220), (box_x, box_y, box_w, box_h), width=2, border_radius=8)

        text = font.render(message, True, _WHITE)
        app.screen.blit(text, text.get_rect(center=(box_x + box_w // 2, box_y + 45)))

        btn_w, btn_h = 220, 50
        self.confirm_keep_rect = pygame.Rect(box_x + 20, box_y + box_h - btn_h - 20, btn_w, btn_h)
        self.confirm_discard_rect = pygame.Rect(box_x + box_w - btn_w - 20, box_y + box_h - btn_h - 20, btn_w, btn_h)

        affordable = player.coins >= cost
        pygame.draw.rect(app.screen, (50, 110, 50) if affordable else (60, 45, 45), self.confirm_keep_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.confirm_keep_rect, width=2, border_radius=8)
        keep_label = font.render("Keep changes" if affordable else "Not enough gold", True, _WHITE)
        app.screen.blit(keep_label, keep_label.get_rect(center=self.confirm_keep_rect.center))

        pygame.draw.rect(app.screen, (110, 50, 50), self.confirm_discard_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.confirm_discard_rect, width=2, border_radius=8)
        discard_label = font.render("Discard changes", True, _WHITE)
        app.screen.blit(discard_label, discard_label.get_rect(center=self.confirm_discard_rect.center))

    def draw_node_tooltip(self, key):
        from systems.bonuses import describe_bonuses
        data = skill_nodes[key]
        points, max_points = points_in(key), data["max_points"]
        header = data["name"] if max_points <= 1 else f"{data['name']}  ({points}/{max_points})"
        lines = [(header, _WHITE)]

        if data["is_root"]:
            lines.append(("Starting point - always active, costs nothing", node_color_on))
        else:
            now = describe_bonuses(node_bonuses(key, points))
            if points > 0 and max_points > 1:
                lines.append(("Now:", _WHITE))
            lines += [(text, _GRAY) for text in now]

            if points < max_points:                           # what the NEXT point adds
                next_lines = describe_bonuses(point_bonus(key, points + 1))
                if max_points > 1:
                    lines.append(("Next point:", _WHITE))
                lines += [(text, (170, 170, 255)) for text in next_lines] or [("Nothing", _GRAY)]
            for at in sorted(data["at_points"]):              # milestones still to come
                if at > points + 1:
                    for text in describe_bonuses(data["at_points"][at]):
                        lines.append((f"At {at} points: {text}", (150, 150, 160)))

            if max_points > 1 and points < data["points_to_pass"]:
                lines.append((f"Needs {data['points_to_pass']} points to continue past it", (220, 170, 90)))
            if can_allocate(player, key):
                lines.append(("Left click: add a point", node_color_available))
            elif points == 0:
                lines.append(("Locked - connect it to the tree first", (200, 80, 80)))
            if points > 0:
                if can_deallocate(key):
                    lines.append((f"Right click: remove a point ({respec_cost_per_point}G if saved)", (255, 120, 90)))
                else:
                    lines.append(("Can't remove - other points depend on this", (200, 80, 80)))

        if data.get("description"):
            lines.append(("", _WHITE))                        # empty line before the flavour text
            lines.append((data["description"], node_flavour_color))
        draw_tooltip_box(lines)

    # --- input --------------------------------------------------------------
    def handle_click(self, pos, button):
        """Mouse DOWN. Left starts a click-or-drag, right removes points."""
        if not self.open:
            return False

        if self.confirm_open:
            if button != 1:
                return True
            if self.confirm_keep_rect and self.confirm_keep_rect.collidepoint(pos):
                if commit_changes(player):
                    self.confirm_open = False
                    self.open = False
            elif self.confirm_discard_rect and self.confirm_discard_rect.collidepoint(pos):
                discard_changes()
                self.confirm_open = False
                self.open = False
            return True

        if button == 1:
            if self.reset_rect and self.reset_rect.collidepoint(pos):
                reset_all(player)
                return True
            self.view.press(pos)                             # a click or a drag: decided on release
            return True

        if button == 3:
            key = self.node_at(pos)
            if key:
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    deallocate_all(key)
                else:
                    deallocate(key)
            return True
        return True

    def handle_release(self, pos, button):
        """Mouse UP. A left click that didn't drag adds points."""
        if not self.open or button != 1 or self.confirm_open:
            return False
        if self.view.release(pos):
            key = self.node_at(pos)
            if key:
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    allocate_all(player, key)
                else:
                    allocate(player, key)
        return True

    def handle_wheel(self, steps):
        if not self.open or self.confirm_open:
            return False
        self.view.scroll(steps, pygame.mouse.get_pos())
        return True

skill_tree_panel = SkillTreePanel()
