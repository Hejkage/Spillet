import pygame
from core.state import app
from core.screen import get_font
from core.assets import scaled_sprites
from systems.items import scale_item_sprite, draw_tooltip_box, gem_slot_support
from systems.supports import support_gem_types
from systems.gemtree import (gem_tree_edges, nodes_for, allocate, can_allocate, points_available, reset_gem_tree,
                              max_gem_level, kills_into_current_level, kills_needed_for_next, supports_gem,
                              enter_tree, has_pending_changes, pending_respec_cost, commit_changes,
                              discard_changes, respec_cost_per_node, can_deallocate, deallocate)

canvas_width = 1600
canvas_height = 1000
base_node_radius = 28

_WHITE = (255, 255, 255)
_GRAY = (200, 200, 200)

class GemTreePanel:
    def __init__(self):
        self.open = False
        self.item = None
        self.node_rects = {}
        self.reset_rect = None
        self.respec_rect = None
        self.respec_mode = False
        self.confirm_open = False
        self.confirm_keep_rect = None
        self.confirm_discard_rect = None

    def open_for(self, item):
        if not nodes_for(item):
            return False
        from ui.panels import open_center_panel
        open_center_panel(None)
        self.item = item
        enter_tree(item)
        self.respec_mode = False
        self.confirm_open = False
        self.open = True
        return True

    def close(self):
        self.request_close()

    def request_close(self):
        if self.item is not None and has_pending_changes(self.item):
            self.confirm_open = True
        else:
            self.open = False
            self.item = None
            self.respec_mode = False

    def canvas_to_screen(self, x, y):
        scale = min(app.screen_width / canvas_width, app.screen_height / canvas_height)
        offset_x = (app.screen_width - canvas_width * scale) / 2
        offset_y = (app.screen_height - canvas_height * scale) / 2
        return int(offset_x + x * scale), int(offset_y + y * scale), scale

    def draw(self):
        if not self.open or self.item is None:
            return
        from systems.items import hover_state
        hover_state.item = None
        hover_state.ground_item = None
        hover_state.ability = None
        item = self.item
        nodes = nodes_for(item)

        overlay = pygame.Surface((app.screen_width, app.screen_height), pygame.SRCALPHA)
        overlay.fill((10, 10, 15, 235))
        app.screen.blit(overlay, (0, 0))

        font = get_font(max(16, int(22 * app.ui_scale)))
        level = item.gem_level()
        header = f"{item.name} — Level {level}/{max_gem_level}   Points: {points_available(item)}"
        app.screen.blit(font.render(header, True, _WHITE), (40, 30))
        if level < max_gem_level:
            progress = f"Kills: {kills_into_current_level(item)} / {kills_needed_for_next(item)}"
        else:
            progress = f"Kills: {item.kills} (max level)"
        app.screen.blit(font.render(progress, True, _GRAY), (40, 30 + font.get_height()))

        from systems.gemtree import tree_supports
        from systems.supports import SupportGem, combine_support_values
        from systems.rarity import rarity_common

        grouped = {}
        for gem in tree_supports(item, item.pending_allocated):
            grouped.setdefault(gem.gem_type, []).append(gem.value)

        if grouped:
            list_y = 30 + font.get_height() * 3
            app.screen.blit(font.render("Active mods:", True, _WHITE), (40, list_y))
            for i, (gem_type, values) in enumerate(grouped.items()):
                combined = SupportGem(gem_type, combine_support_values(gem_type, values), rarity_common)
                app.screen.blit(font.render(combined.describe(), True, _GRAY), (40, list_y + font.get_height() * (i + 1)))

        edges = gem_tree_edges.get(item.template_key, {})
        drawn = set()
        for key, neighbor_keys in edges.items():
            for other in neighbor_keys:
                edge = tuple(sorted((key, other)))
                if edge in drawn:
                    continue
                drawn.add(edge)
                x1, y1, _ = self.canvas_to_screen(*nodes[key]["position"])
                x2, y2, _ = self.canvas_to_screen(*nodes[other]["position"])
                both = key in item.pending_allocated and other in item.pending_allocated
                pygame.draw.line(app.screen, (120, 200, 120) if both else (80, 80, 90), (x1, y1), (x2, y2), 4)

        self.node_rects = {}
        hovered = None
        mouse_pos = pygame.mouse.get_pos()
        for key, data in nodes.items():
            x, y, scale = self.canvas_to_screen(*data["position"])
            radius = max(10, int(base_node_radius * scale))
            if key in item.pending_allocated:
                color = (240, 200, 60)
            elif can_allocate(item, key):
                color = (140, 140, 255)
            else:
                color = (70, 70, 75)
            pygame.draw.circle(app.screen, color, (x, y), radius)
            border_color = (255, 120, 90) if (self.respec_mode and key in item.pending_allocated and can_deallocate(item, key)) else _WHITE
            pygame.draw.circle(app.screen, border_color, (x, y), radius, 3)

            sprite_name = data.get("sprite_name")
            if sprite_name and sprite_name in scaled_sprites:
                fitted = scale_item_sprite(scaled_sprites[sprite_name], radius * 1.6)
                app.screen.blit(fitted, fitted.get_rect(center=(x, y)))

            if data.get("is_socket"):
                socketed = item.sockets.get(key)
                if socketed is not None:
                    gem_sprite = scaled_sprites.get(socketed.sprite_name)
                    if gem_sprite:
                        fitted = scale_item_sprite(gem_sprite, radius * 1.4)
                        app.screen.blit(fitted, fitted.get_rect(center=(x, y)))
                else:
                    pygame.draw.circle(app.screen, (30, 30, 35), (x, y), int(radius * 0.55))

            label = font.render(data["name"], True, _WHITE)
            app.screen.blit(label, label.get_rect(midtop=(x, y + radius + 6)))
            self.node_rects[key] = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
            if self.node_rects[key].collidepoint(mouse_pos):
                hovered = key

        btn_w, btn_h = 200, 50
        self.reset_rect = pygame.Rect(app.screen_width - btn_w - 40, app.screen_height - btn_h - 40, btn_w, btn_h)
        pygame.draw.rect(app.screen, (120, 40, 40), self.reset_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.reset_rect, width=2, border_radius=8)
        app.screen.blit(font.render("Reset All", True, _WHITE), font.render("Reset All", True, _WHITE).get_rect(center=self.reset_rect.center))

        self.respec_rect = pygame.Rect(self.reset_rect.left - btn_w - 20, self.reset_rect.top, btn_w, btn_h)
        respec_fill = (60, 110, 60) if self.respec_mode else (60, 60, 90)
        pygame.draw.rect(app.screen, respec_fill, self.respec_rect, border_radius=8)
        pygame.draw.rect(app.screen, (220, 220, 220), self.respec_rect, width=2, border_radius=8)
        respec_label = font.render(f"Respec ({respec_cost_per_node}G/node)", True, _WHITE)
        app.screen.blit(respec_label, respec_label.get_rect(center=self.respec_rect.center))

        if hovered and not self.confirm_open:
            self.draw_node_tooltip(hovered)

        if self.confirm_open:
            self.draw_confirm_prompt()

    def draw_confirm_prompt(self):
        font = get_font(max(16, int(22 * app.ui_scale)))
        cost = pending_respec_cost(self.item)
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

        from systems.player import player
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
        data = nodes_for(self.item)[key]
        lines = [(data["name"], _WHITE)]

        if data.get("is_socket"):
            socketed = self.item.sockets.get(key)
            if socketed is not None:
                lines.append((socketed.support_gem.describe(), _GRAY))
            else:
                lines.append(("Empty socket", _GRAY))
                from systems.items import drag_state
                held = drag_state.item
                if held is not None and getattr(held, "gem_slot", None) == gem_slot_support and not supports_gem(held, self.item):
                    lines.append((f"{self.item.name} cannot be supported by this gem", (200, 80, 80)))
        elif data["support_type"]:
            from systems.supports import SupportGem
            from systems.rarity import rarity_common
            lines.append((SupportGem(data["support_type"], data["value"], rarity_common).describe(), _GRAY))
        elif data["stats"]:
            from systems.pets import describe_pet_mod
            for mod in data["stats"]:
                lines.append((describe_pet_mod(mod), _GRAY))
        else:
            lines.append(("No effect", _GRAY))

        if key in self.item.pending_allocated:
            if self.respec_mode:
                if can_deallocate(self.item, key):
                    lines.append((f"Click to unallocate ({respec_cost_per_node}G)", (255, 120, 90)))
                else:
                    lines.append(("Can't unallocate this node", (200, 80, 80)))
            else:
                lines.append(("Allocated", (240, 200, 60)))
        elif can_allocate(self.item, key):
            lines.append(("Click to allocate", (140, 140, 255)))
        else:
            lines.append(("Locked", (200, 80, 80)))
        draw_tooltip_box(lines)

    def handle_click(self, pos, button, drag_state):
        if not self.open or button != 1:
            return False
        from systems.player import player
        item = self.item
        nodes = nodes_for(item)

        if self.confirm_open:
            if self.confirm_keep_rect and self.confirm_keep_rect.collidepoint(pos):
                if commit_changes(item, player):
                    self.confirm_open = False
                    self.open = False
                    self.respec_mode = False
                    self.item = None
            elif self.confirm_discard_rect and self.confirm_discard_rect.collidepoint(pos):
                discard_changes(item)
                self.confirm_open = False
                self.open = False
                self.respec_mode = False
                self.item = None
            return True

        if self.reset_rect and self.reset_rect.collidepoint(pos):
            reset_gem_tree(item)
            player.gem_signature = None
            return True

        if self.respec_rect and self.respec_rect.collidepoint(pos):
            self.respec_mode = not self.respec_mode
            return True

        for key, rect in self.node_rects.items():
            if not rect.collidepoint(pos):
                continue
            data = nodes[key]
            if data.get("is_socket"):
                current = item.sockets.get(key)
                if drag_state.item is None:
                    if current is not None:
                        item.sockets[key] = None
                        drag_state.item = current
                        drag_state.source = ("gem_socket", key)
                    elif self.respec_mode:
                        deallocate(item, key)
                    else:
                        allocate(item, key)
                elif (getattr(drag_state.item, "gem_slot", None) == gem_slot_support
                      and key in item.pending_allocated
                      and supports_gem(drag_state.item, item)):
                    item.sockets[key] = drag_state.item
                    drag_state.item = current
                    drag_state.source = None
                return True
            if self.respec_mode:
                deallocate(item, key)
            else:
                allocate(item, key)
            return True
        return True

gem_tree_panel = GemTreePanel()