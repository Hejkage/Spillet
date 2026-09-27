import pygame
from core.state import app
from core.screen import get_font
from core.assets import scaled_sprites
from systems.skilltree import skill_nodes, adjacency, allocated_nodes, can_allocate, allocate, reset_all, points_available
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

    def toggle(self):
        self.open = not self.open

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
                both_allocated = key in allocated_nodes and other in allocated_nodes
                color = (120, 200, 120) if both_allocated else (80, 80, 90)
                pygame.draw.line(app.screen, color, (x1, y1), (x2, y2), 4)

        self.node_rects = {}
        hovered_key = None                    
        mouse_pos = pygame.mouse.get_pos()    
        for key, data in skill_nodes.items():
            x, y, scale = self.canvas_to_screen(*data["position"])
            radius = max(10, int(base_node_radius * scale))
            if key in allocated_nodes:
                color = (240, 200, 60)
            elif can_allocate(player, key):
                color = (140, 140, 255)
            else:
                color = (70, 70, 75)
            pygame.draw.circle(app.screen, color, (x, y), radius)
            pygame.draw.circle(app.screen, (255, 255, 255), (x, y), radius, 3)

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

        if hovered_key:
            self.draw_node_tooltip(hovered_key)

    def handle_click(self, pos, button):
        if not self.open or button != 1:
            return False
        if self.reset_rect and self.reset_rect.collidepoint(pos):
            reset_all(player)
            return True
        for key, rect in self.node_rects.items():
            if rect.collidepoint(pos):
                allocate(player, key)
                return True
        return True

    def draw_node_tooltip(self, key):
        data = skill_nodes[key]
        lines = [(data["name"], _WHITE)]
        if data["stats"]:
            for mod in data["stats"]:
                lines.append((_mod_line(mod), _GRAY))
        else:
            lines.append(("No stats", _GRAY))
        if key in allocated_nodes:
            lines.append(("Allocated", (240, 200, 60)))
        elif can_allocate(player, key):
            lines.append(("Click to allocate", (140, 140, 255)))
        else:
            lines.append(("Locked — connect it to an allocated point", (200, 80, 80)))
        draw_tooltip_box(lines)

skill_tree_panel = SkillTreePanel() 