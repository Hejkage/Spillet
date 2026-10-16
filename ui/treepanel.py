"""TREE PANEL - the screen for EVERY tree (the passive tree, gem trees, pet trees).

It draws one TreeProgress (systems/trees.py): the lines, the nodes, the tooltips,
and handles clicks, sockets, zoom and the keep/discard prompt.

What differs per kind of tree is small, so it is a few methods a smaller
class can replace (ui/skilltree.py, ui/gemtree.py):

    header_lines()         the text in the top left
    can_socket(item)       may this held item go in a socket?
    socket_lines(item)     tooltip lines for the item in a socket
    after_reset()          after the Reset All button

Controls (the same in every tree):
    Left click: add a point     Right click: remove one     Ctrl: all at once
    Left click a socket: put the held item in / take the item out
    Left click a locked section's start: unlock it   Right click: lock it again (when empty)
    Choice nodes are split: click the half you want (click the other half later to switch)
    Drag / WASD: move           Wheel: zoom
"""
import pygame
from core.state import app
from core.screen import get_font
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
section_locked_shade = (10, 10, 15, 150) # drawn over every node of a locked section
section_label_color  = (230, 210, 160)
one_way_arrow_size   = 10                # tree pixels at 100% zoom
choice_hover_color   = (255, 255, 255, 60)   # the half of a choice node under the mouse
labels_from_zoom     = 1                 # node names are shown from this zoom and up
show_node_names      = False

help_text = "Left click: add point   Right click: remove   Ctrl: all at once   Drag / WASD: move   Wheel: zoom"

class TreePanel:
    def __init__(self):
        self.open = False
        self.progress = None             # the TreeProgress being shown
        self.view = TreeView()
        self.node_spots = {}             # key -> (x, y, radius) on screen, from the last draw
        self.reset_rect = None
        self.confirm_open = False
        self.confirm_keep_rect = None
        self.confirm_discard_rect = None

    # --- what a smaller class replaces -------------------------------------
    def header_lines(self):
        return [(f"Points: {self.progress.points_available()}", _WHITE)]

    def can_socket(self, item):
        return False

    def socket_lines(self, item):
        return [(item.name, _GRAY)]

    def after_reset(self):
        pass

    # --- opening and closing -----------------------------------------------
    def show(self, progress, fit=True):
        """Open the screen on this progress (one owner's points in one tree)."""
        self.progress = progress
        progress.start_edit()
        if fit or not self.view.fitted:
            self.view.fit(d["position"] for d in progress.tree.nodes.values())
        self.confirm_open = False
        self.open = True

    def request_close(self):
        if self.progress is not None and self.progress.has_changes():
            self.confirm_open = True
        else:
            self.finish()

    def close(self):
        self.request_close()

    def finish(self):
        self.open = False
        self.confirm_open = False

    def node_at(self, pos):
        for key, (x, y, radius) in self.node_spots.items():
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= radius ** 2:
                return key
        return None

    # --- drawing ------------------------------------------------------------
    def draw(self):
        if not self.open or self.progress is None:
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

        self.draw_edges()
        self.draw_nodes()

        # --- header, help and buttons ---
        font = get_font(max(16, int(22 * app.ui_scale)))
        small_font = get_font(max(12, int(16 * app.ui_scale)))
        y = 30
        for text, color in self.header_lines():
            app.screen.blit(font.render(text, True, color), (40, y))
            y += font.get_height()
        app.screen.blit(small_font.render(help_text, True, (160, 160, 170)), (40, y + 4))

        btn_w, btn_h = 200, 50
        self.reset_rect = pygame.Rect(app.screen_width - btn_w - 40, app.screen_height - btn_h - 40, btn_w, btn_h)
        pygame.draw.rect(app.screen, (120, 40, 40), self.reset_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.reset_rect, width=2, border_radius=8)
        reset_label = font.render("Reset All", True, _WHITE)
        app.screen.blit(reset_label, reset_label.get_rect(center=self.reset_rect.center))

        hovered_key = self.node_at(pygame.mouse.get_pos())
        if hovered_key and not self.confirm_open and not self.view.dragging:
            self.draw_node_tooltip(hovered_key)

        if self.confirm_open:
            self.draw_confirm_prompt()

    def draw_edges(self):
        progress, tree, view = self.progress, self.progress.tree, self.view
        drawn = set()
        for key, neighbor_keys in tree.adjacency.items():
            for other in neighbor_keys:
                edge = tuple(sorted((key, other)))
                if edge in drawn or key not in tree.nodes or other not in tree.nodes:
                    continue
                drawn.add(edge)
                lit = (progress.node_is_on(key) and progress.node_is_on(other)
                       and (progress.is_passable(key) or progress.is_passable(other)))
                color = edge_color_on if lit else edge_color_off
                start = view.to_screen(*tree.nodes[key]["position"])
                end = view.to_screen(*tree.nodes[other]["position"])
                pygame.draw.line(app.screen, color, start, end, max(2, int(4 * view.zoom)))
                for a, b in ((key, other), (other, key)):
                    if (a, b) in tree.one_way:                # an arrow in the middle: a unlocks b
                        self.draw_arrow(view.to_screen(*tree.nodes[a]["position"]),
                                        view.to_screen(*tree.nodes[b]["position"]), color)

    def draw_arrow(self, start, end, color):
        direction = pygame.Vector2(end) - pygame.Vector2(start)
        if direction.length() == 0:
            return
        direction.scale_to_length(one_way_arrow_size * self.view.zoom)
        tip = (pygame.Vector2(start) + pygame.Vector2(end)) / 2 + direction
        left = tip - direction * 2 + direction.rotate(90)
        right = tip - direction * 2 + direction.rotate(-90)
        pygame.draw.polygon(app.screen, color, [tip, left, right])

    def draw_nodes(self):
        progress, tree, view = self.progress, self.progress.tree, self.view
        zoom = view.zoom
        small_font = get_font(max(12, int(16 * app.ui_scale)))
        self.node_spots = {}
        for key, data in tree.nodes.items():
            x, y = view.to_screen(*data["position"])
            size = tree.size(key)
            radius = max(3, int(size * zoom / 2))
            if x < -radius or y < -radius or x > app.screen_width + radius or y > app.screen_height + radius:
                continue                                      # off screen
            self.node_spots[key] = (x, y, radius)
            points = progress.points_in(key)
            if progress.node_is_on(key):
                color = node_color_full if (points >= data["max_points"] and not data["is_root"]) else node_color_on
            elif progress.can_allocate(key):
                color = node_color_available
            else:
                color = node_color_locked

            frame = view.sprite(data["frame"], size) if data["frame"] else None
            art = data["sprite_name"]
            if data["choices"] and progress.choice_of(key) is not None:      # a picked choice shows its own art
                art = data["choices"][progress.choice_of(key)]["sprite_name"] or art
            icon = view.sprite(art, size) if art else None
            if frame:
                app.screen.blit(frame, frame.get_rect(center=(x, y)))
            else:                                                       # no border yet: the old circle
                pygame.draw.circle(app.screen, color, (x, y), radius)
                pygame.draw.circle(app.screen, _WHITE, (x, y), radius, max(1, int(2 * zoom)))
            if icon:
                app.screen.blit(icon, icon.get_rect(center=(x, y)))     # art on top of the border

            if data["choices"]:
                self.draw_choice_split(key, x, y, radius)

            if data["is_socket"]:                                       # the item in the socket
                held = progress.sockets.get(key)
                held_sprite = view.sprite(held.sprite_name, size * 0.7) if held is not None else None
                if held_sprite:
                    app.screen.blit(held_sprite, held_sprite.get_rect(center=(x, y)))
                elif held is None:
                    pygame.draw.circle(app.screen, (30, 30, 35), (x, y), int(radius * 0.55))

            if not progress.node_open(key):                             # a locked section: darker
                shade = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(shade, section_locked_shade, (radius, radius), radius)
                app.screen.blit(shade, (x - radius, y - radius))

            if data["is_root"] and data["section"] is not None:         # the section's name above its start
                name = tree.sections[data["section"]]["name"]
                state = "" if progress.node_open(key) else "  (locked)"
                label = get_font(max(14, int(20 * app.ui_scale))).render(name + state, True, section_label_color)
                app.screen.blit(label, label.get_rect(midbottom=(x, y - radius - 4)))
            text_y = y + radius + 2
            if data["max_points"] > 1:
                counter = small_font.render(f"{points}/{data['max_points']}", True, _WHITE)
                app.screen.blit(counter, counter.get_rect(midtop=(x, text_y)))
                text_y += counter.get_height()
            if show_node_names and zoom >= labels_from_zoom:
                label = small_font.render(data["name"], True, _GRAY)
                app.screen.blit(label, label.get_rect(midtop=(x, text_y)))

    def choice_at(self, key, pos):
        """Which choice of a choice node is under pos: the node is cut into equal
        slices from left to right (2 choices = left half / right half)."""
        x, y, radius = self.node_spots[key]
        count = len(self.progress.tree.nodes[key]["choices"])
        slot = int((pos[0] - (x - radius)) / max(1, 2 * radius) * count)
        return max(0, min(count - 1, slot))

    def draw_choice_split(self, key, x, y, radius):
        """Lines between the choices, the hovered slice lit up, and a dot on the picked one."""
        count = len(self.progress.tree.nodes[key]["choices"])
        width = 2 * radius / count
        for i in range(1, count):
            line_x = int(x - radius + width * i)
            pygame.draw.line(app.screen, _WHITE, (line_x, y - radius), (line_x, y + radius), max(1, int(2 * self.view.zoom)))
        mouse = pygame.mouse.get_pos()
        if self.node_at(mouse) == key and not self.confirm_open:
            i = self.choice_at(key, mouse)
            glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, choice_hover_color, (radius, radius), radius)
            keep = pygame.Rect(int(width * i), 0, int(width) + 1, radius * 2)       # only the hovered slice
            app.screen.blit(glow, (x - radius + keep.x, y - radius), keep)
        picked = self.progress.choice_of(key)
        if picked is not None:
            dot_x = int(x - radius + width * (picked + 0.5))
            pygame.draw.circle(app.screen, node_color_on, (dot_x, y + radius - 3), max(2, int(3 * self.view.zoom)))

    def draw_confirm_prompt(self):
        from systems.player import player
        font = get_font(max(16, int(22 * app.ui_scale)))
        cost = self.progress.respec_cost()
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

    def section_lines(self, section):
        """Tooltip lines for a section's start node."""
        progress, tree = self.progress, self.progress.tree
        lines = [(f"Section: {tree.sections[section]['name']}", section_label_color)]
        if progress.section_open(section):
            lines.append(("Unlocked", node_color_on))
            if progress.can_lock_section(section):
                extra = (f" (costs {tree.section_lock_cost} gold when kept)"
                         if section in progress.saved_sections else "")
                lines.append((f"Right click: lock it again and get the section point back{extra}", (170, 170, 255)))
            else:
                lines.append(("Take every point out of it to lock it again", (150, 150, 160)))
        elif progress.can_unlock_section(section):
            lines.append(("Click to unlock (uses 1 section point)", node_color_available))
        else:
            lines.append(("Locked - no section points left", (200, 80, 80)))
        return lines

    def bonus_lines(self, key, points, choice=None):
        """What a node (or one of its choices) gives now, with its next point, and later."""
        tree, data = self.progress.tree, self.progress.tree.nodes[key]
        table = tree.bonus_table(key, choice)
        max_points = data["max_points"]
        lines = []
        now = tree.describe(tree.node_bonuses(key, points, choice))
        if points > 0 and max_points > 1:
            lines.append(("Now:", _WHITE))
        lines += [(text, _GRAY) for text in now]

        if points < max_points:                               # what the NEXT point adds
            next_lines = tree.describe(tree.point_bonus(key, points + 1, choice))
            if max_points > 1:
                lines.append(("Next point:", _WHITE))
            if next_lines or not data["is_socket"]:
                lines += [(text, (170, 170, 255)) for text in next_lines] or [("Nothing", _GRAY)]
        # milestones still to come. The same text on several points in a row
        # is one line: "Points 3-9: +1% Fire Resistance each"
        upcoming = [(at, tree.describe(table["at_points"][at]))
                    for at in sorted(table["at_points"]) if at > points + 1]
        i = 0
        while i < len(upcoming):
            at, texts = upcoming[i]
            last = at
            while i + 1 < len(upcoming) and upcoming[i + 1][1] == texts and upcoming[i + 1][0] == last + 1:
                i += 1
                last = upcoming[i][0]
            for text in texts:
                label = f"At {at} points: {text}" if last == at else f"Points {at}-{last}: {text} each"
                lines.append((label, (150, 150, 160)))
            i += 1
        return lines

    def draw_node_tooltip(self, key):
        from systems.items import draw_tooltip_box, drag_state
        progress, tree = self.progress, self.progress.tree
        data = tree.nodes[key]
        points, max_points = progress.points_in(key), data["max_points"]
        header = data["name"] if max_points <= 1 else f"{data['name']}  ({points}/{max_points})"
        lines = [(header, _WHITE)]

        section = data["section"]
        if data["is_root"] and section is not None:
            lines += self.section_lines(section)
        elif data["is_root"]:
            lines.append(("Starting point - always active, costs nothing", node_color_on))
        else:
            if not progress.node_open(key):
                lines.append((f"In the locked section {tree.sections[section]['name']}", (200, 80, 80)))
            if data["is_socket"]:
                held = progress.sockets.get(key)
                if held is not None:
                    lines += self.socket_lines(held)
                else:
                    lines.append(("Empty socket", _GRAY))
                    if drag_state.item is not None and not self.can_socket(drag_state.item):
                        lines.append(("That item can't go in this socket", (200, 80, 80)))
                if points == 0:
                    lines.append(("Put a point in it to use the socket", (220, 170, 90)))

            if data["cost"] > 1:
                each = "Each point costs" if max_points > 1 else "Costs"
                lines.append((f"{each} {data['cost']} skill points", (220, 170, 90)))

            if data["choices"]:                               # every option, the picked / hovered one marked
                picked = progress.choice_of(key)
                hovered = self.choice_at(key, pygame.mouse.get_pos())
                side = ["left", "right"] if len(data["choices"]) == 2 else None
                for i, option in enumerate(data["choices"]):
                    if i == picked:
                        mark, color = "  (picked)", node_color_on
                    elif i == hovered:
                        mark, color = "  (click to pick)" if picked is None else "  (click to switch)", node_color_available
                    else:
                        mark, color = (f"  ({side[i]} half)" if side else ""), _GRAY
                    lines.append(("", _WHITE))
                    lines.append((option["name"] + mark, color))
                    lines += self.bonus_lines(key, points if i == picked else 0, i)
            else:
                lines += self.bonus_lines(key, points)

            if max_points > 1 and points < data["points_to_pass"]:
                lines.append((f"Needs {data['points_to_pass']} points to continue past it", (220, 170, 90)))
            if points == 0 and not progress.can_allocate(key):
                if progress.node_open(key) and progress.points_available() < data["cost"]:
                    lines.append((f"Needs {data['cost']} free skill points", (200, 80, 80)))
                else:
                    lines.append(("Locked - connect it to the tree first", (200, 80, 80)))
            if points > 0 and not progress.can_deallocate(key):
                reason = ("Take the gem out first" if points == 1 and progress.sockets.get(key) is not None
                          else "Can't remove - other points depend on this")
                lines.append((reason, (200, 80, 80)))

        if data.get("description"):
            lines.append(("", _WHITE))                        # empty line before the flavour text
            lines.append((data["description"], node_flavour_color))
        draw_tooltip_box(lines)

    # --- input --------------------------------------------------------------
    def handle_click(self, pos, button, drag_state=None):
        """Mouse DOWN. Left starts a click-or-drag, right removes points."""
        if not self.open:
            return False
        from systems.player import player

        if self.confirm_open:
            if button != 1:
                return True
            if self.confirm_keep_rect and self.confirm_keep_rect.collidepoint(pos):
                if self.progress.commit(player):
                    self.finish()
            elif self.confirm_discard_rect and self.confirm_discard_rect.collidepoint(pos):
                self.progress.discard()
                self.finish()
            return True

        if button == 1:
            if self.reset_rect and self.reset_rect.collidepoint(pos):
                self.progress.reset(player)
                self.after_reset()
                return True
            self.view.press(pos)                             # a click or a drag: decided on release
            return True

        if button == 3:
            key = self.node_at(pos)
            if key and self.progress.tree.nodes[key]["is_root"]:
                section = self.progress.tree.nodes[key]["section"]
                if section is not None:
                    self.progress.lock_section(section)
            elif key:
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.progress.deallocate_all(key)
                else:
                    self.progress.deallocate(key)
            return True
        return True

    def handle_release(self, pos, button, drag_state=None):
        """Mouse UP. A left click that didn't drag uses the node under the mouse."""
        if not self.open or button != 1 or self.confirm_open:
            return False
        if not self.view.release(pos):
            return True                                      # it was a drag
        key = self.node_at(pos)
        if key is None:
            return True
        data = self.progress.tree.nodes[key]
        if data["is_root"] and data["section"] is not None:
            self.progress.unlock_section(data["section"])
            return True
        if data["is_socket"] and self.use_socket(key):
            return True
        choice = self.choice_at(key, pos) if data["choices"] else None
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.progress.allocate_all(key, choice)
        else:
            self.progress.allocate(key, choice)
        return True

    def use_socket(self, key):
        """Put the held item in / take the item out. False if nothing happened
        (then the click adds a point instead)."""
        from systems.items import drag_state
        progress = self.progress
        current = progress.sockets.get(key)
        held = drag_state.item
        if held is None:
            if current is None:
                return False
            progress.sockets[key] = None                     # pick it up
            drag_state.item = current
            drag_state.source = None
        elif progress.points_in(key) > 0 and self.can_socket(held):
            progress.sockets[key] = held                     # put it in (swap with what was there)
            drag_state.item = current
            drag_state.source = None
        else:
            return False
        from systems.player import player
        player.gem_signature = None                          # the gem's supports changed
        return True

    def handle_wheel(self, steps):
        if not self.open or self.confirm_open:
            return False
        self.view.scroll(steps, pygame.mouse.get_pos())
        return True
