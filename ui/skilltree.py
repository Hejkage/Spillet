import pygame
from core.state import app
from core.screen import get_font
from core.assets import scaled_sprites
from systems.skilltree import (skill_nodes, adjacency, pending_nodes, can_allocate, allocate, can_deallocate, deallocate, reset_all, points_available, enter_tree, has_pending_changes, pending_respec_cost, commit_changes, discard_changes, respec_cost_per_node, node_lines, node_is_on)
from systems.player import player
from systems.items import scale_item_sprite, draw_tooltip_box, stat_label, stat_is_percent

canvas_width = 1600
canvas_height = 1000
base_node_radius = 28

_WHITE = (255, 255, 255)
_GRAY = (200, 200, 200)

def _mod_line(mod):
    stat = mod.get("stat")
    label = stat_label(stat)
    amount = mod.get("amount", 0)
    mod_type = mod.get("type")
    if mod_type == "flat":
        suffix = "%" if stat_is_percent(stat) else ""
        return f"+{amount}{suffix} {label}"
    elif mod_type == "increased":
        return f"+{amount}% increased {label}"
    elif mod_type == "more":
        return f"+{amount}% {label}"
    return f"{amount} {label}"

class SkillTreePanel:
    def __init__(self):
        self.open = False
        self.node_rects = {}
        self.reset_rect = None
        self.respec_rect = None
        self.respec_mode = False
        self.confirm_open = False
        self.confirm_keep_rect = None
        self.confirm_discard_rect = None

    def toggle(self):
        if self.open:
            self.request_close()
        else:
            enter_tree()
            self.open = True

    def request_close(self):
        if has_pending_changes():
            self.confirm_open = True
        else:
            self.open = False
            self.respec_mode = False

    def canvas_to_screen(self, x, y):
        scale = min(app.screen_width / canvas_width, app.screen_height / canvas_height)
        offset_x = (app.screen_width - canvas_width * scale) / 2
        offset_y = (app.screen_height - canvas_height * scale) / 2
        return int(offset_x + x * scale), int(offset_y + y * scale), scale

    def draw(self):
        if not self.open:
            return

        from systems.items import hover_state
        hover_state.item = None
        hover_state.ability = None
        hover_state.ground_item = None

        overlay = pygame.Surface((app.screen_width, app.screen_height), pygame.SRCALPHA)
        overlay.fill((10, 10, 15, 235))
        app.screen.blit(overlay, (0, 0))

        font = get_font(max(16, int(22 * app.ui_scale)))
        title = font.render(f"Skill Points: {points_available(player)}", True, (255, 255, 255))
        app.screen.blit(title, (40, 30))

        drawn_edges = set()
        for key, neighbor_keys in adjacency.items():
            for other in neighbor_keys:
                edge = tuple(sorted((key, other)))
                if edge in drawn_edges:
                    continue
                drawn_edges.add(edge)
                x1, y1, _ = self.canvas_to_screen(*skill_nodes[key]["position"])
                x2, y2, _ = self.canvas_to_screen(*skill_nodes[other]["position"])
                both_allocated = node_is_on(key) and node_is_on(other)
                color = (120, 200, 120) if both_allocated else (80, 80, 90)
                pygame.draw.line(app.screen, color, (x1, y1), (x2, y2), 4)

        self.node_rects = {}
        hovered_key = None
        mouse_pos = pygame.mouse.get_pos()
        for key, data in skill_nodes.items():
            x, y, scale = self.canvas_to_screen(*data["position"])
            radius = max(10, int(base_node_radius * scale))
            if node_is_on(key):
                color = (240, 200, 60)
            elif can_allocate(player, key):
                color = (140, 140, 255)
            else:
                color = (70, 70, 75)
            pygame.draw.circle(app.screen, color, (x, y), radius)
            border_color = (255, 120, 90) if (self.respec_mode and key in pending_nodes and can_deallocate(key)) else (255, 255, 255)
            pygame.draw.circle(app.screen, border_color, (x, y), radius, 3)

            sprite_name = data.get("sprite_name")
            if sprite_name and sprite_name in scaled_sprites:
                fitted = scale_item_sprite(scaled_sprites[sprite_name], radius * 1.6)
                app.screen.blit(fitted, fitted.get_rect(center=(x, y)))

            label = font.render(data["name"], True, (255, 255, 255))
            app.screen.blit(label, label.get_rect(midtop=(x, y + radius + 6)))
            self.node_rects[key] = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
            if self.node_rects[key].collidepoint(mouse_pos):
                hovered_key = key

        btn_w, btn_h = 200, 50
        self.reset_rect = pygame.Rect(app.screen_width - btn_w - 40, app.screen_height - btn_h - 40, btn_w, btn_h)
        pygame.draw.rect(app.screen, (120, 40, 40), self.reset_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.reset_rect, width=2, border_radius=8)
        reset_label = font.render("Reset All", True, (255, 255, 255))
        app.screen.blit(reset_label, reset_label.get_rect(center=self.reset_rect.center))

        self.respec_rect = pygame.Rect(self.reset_rect.left - btn_w - 20, self.reset_rect.top, btn_w, btn_h)
        respec_fill = (60, 110, 60) if self.respec_mode else (60, 60, 90)
        pygame.draw.rect(app.screen, respec_fill, self.respec_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.respec_rect, width=2, border_radius=8)
        respec_label = font.render(f"Respec ({respec_cost_per_node}G/node)", True, (255, 255, 255))
        app.screen.blit(respec_label, respec_label.get_rect(center=self.respec_rect.center))

        if hovered_key and not self.confirm_open:
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

        text = font.render(message, True, (255, 255, 255))
        app.screen.blit(text, text.get_rect(center=(box_x + box_w // 2, box_y + 45)))

        btn_w, btn_h = 220, 50
        self.confirm_keep_rect = pygame.Rect(box_x + 20, box_y + box_h - btn_h - 20, btn_w, btn_h)
        self.confirm_discard_rect = pygame.Rect(box_x + box_w - btn_w - 20, box_y + box_h - btn_h - 20, btn_w, btn_h)

        affordable = player.coins >= cost
        pygame.draw.rect(app.screen, (50, 110, 50) if affordable else (60, 45, 45), self.confirm_keep_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.confirm_keep_rect, width=2, border_radius=8)
        keep_label = font.render("Keep changes" if affordable else "Not enough gold", True, (255, 255, 255))
        app.screen.blit(keep_label, keep_label.get_rect(center=self.confirm_keep_rect.center))

        pygame.draw.rect(app.screen, (110, 50, 50), self.confirm_discard_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.confirm_discard_rect, width=2, border_radius=8)
        discard_label = font.render("Discard changes", True, (255, 255, 255))
        app.screen.blit(discard_label, discard_label.get_rect(center=self.confirm_discard_rect.center))

    def handle_click(self, pos, button):
        if not self.open or button != 1:
            return False

        if self.confirm_open:
            if self.confirm_keep_rect and self.confirm_keep_rect.collidepoint(pos):
                if commit_changes(player):
                    self.confirm_open = False
                    self.open = False
                    self.respec_mode = False
            elif self.confirm_discard_rect and self.confirm_discard_rect.collidepoint(pos):
                discard_changes()
                self.confirm_open = False
                self.open = False
                self.respec_mode = False
            return True

        if self.reset_rect and self.reset_rect.collidepoint(pos):
            reset_all(player)
            return True

        if self.respec_rect and self.respec_rect.collidepoint(pos):
            self.respec_mode = not self.respec_mode
            return True

        for key, rect in self.node_rects.items():
            if rect.collidepoint(pos):
                if self.respec_mode:
                    deallocate(key)
                else:
                    allocate(player, key)
                return True
        return True

    def draw_node_tooltip(self, key):
        data = skill_nodes[key]
        lines = [(data["name"], _WHITE)]
        if data.get("description"):
            lines.append((data["description"], (170, 170, 190)))
        described = node_lines(key)
        if described:
            for text in described:
                lines.append((text, _GRAY))
        elif not data["is_root"] and not data.get("description"):
            lines.append(("Does nothing yet", _GRAY))
        if data["is_root"]:
            lines.append(("Starting point — always active, costs nothing", (240, 200, 60)))
        elif key in pending_nodes:
            if self.respec_mode:
                if can_deallocate(key):
                    lines.append((f"Click to unallocate ({respec_cost_per_node}G)", (255, 120, 90)))
                else:
                    lines.append(("Can't unallocate — other points depend on this", (200, 80, 80)))
            else:
                lines.append(("Allocated", (240, 200, 60)))
        elif can_allocate(player, key):
            lines.append(("Click to allocate", (140, 140, 255)))
        else:
            lines.append(("Locked — connect it to an allocated point", (200, 80, 80)))
        draw_tooltip_box(lines)

skill_tree_panel = SkillTreePanel()