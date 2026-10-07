import pygame
import random
from core.state import app
from core.screen import get_font, place_centre_window, place_bottom_right_window
from core.assets import get_ui_scaled, scaled_sprites, draw_window, window_size, check_window_fits
from systems.rarity import rarity_common, rarity_epic, rarity_legendary, rarity_rare, rarity_uncommon
from systems.items import equipment, hover_state, scale_item_sprite
from systems.player import player
from ui.skilltree import skill_tree_panel
from ui.gemtree import gem_tree_panel

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Inventory
inventory_collums = 4
inventory_rows = 6
inventory_slot_size = 64
inventory_padding = 4

class Bag():
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.slots = [None] * (cols * rows)

    def add_item(self, item):
        for i, slot in enumerate(self.slots):
            if slot is None:
                self.slots[i] = item
                return  True
        return False

    def remove_item(self, index):
        item = self.slots[index]
        self.slots[index] = None
        return item

grid_containers = []

def open_center_panel(panel):
    for c in grid_containers:
        if c.is_center_panel:
            c.open = (c is panel)
    equipment.open = (equipment is panel)

def attack_blocking_panel_open():
    if equipment.open:
        return True
    if skill_tree_panel.open:
        return True
    if gem_tree_panel.open:
        return True
    return any(c.open and c.is_center_panel for c in grid_containers)

class GridContainer:
    source_kind = "container"
    is_center_panel = True                
    window = "chest"                     # which register_window() size this uses (core/assets.py)
    slot_sprite_name = "inventory_slot_sprite"
    base_slot_size = 64
    base_padding = 4
    base_row_extra = 0       

    def __init__(self, cols, rows):
        self.bags = [Bag(cols, rows)]
        self.open = False
        self.rect = None
        self.slot_size = self.base_slot_size
        self.padding = self.base_padding
        self.row_extra = self.base_row_extra 
        self.panel_padding = 16
        grid_containers.append(self)

    def toggle(self):
        self.open = not self.open

    def grid_origin(self):
        """Top-left of the first slot: the grid is centred left-to-right in the window."""
        bag = self.bags[0]
        grid_width = bag.cols * (self.slot_size + self.padding) - self.padding
        ox = self.rect.x + (self.rect.width - grid_width) // 2
        oy = self.rect.y + self.panel_padding + self.extra_content_top(app.ui_scale)
        return ox, oy
    
    def get_slot_rect(self, bag_index, slot_index, origin_x, origin_y):
        bag = self.bags[bag_index]
        col = slot_index % bag.cols
        row = slot_index // bag.cols
        x = origin_x + col * (self.slot_size + self.padding)
        y = origin_y + row * (self.slot_size + self.padding + self.row_extra)
        return pygame.Rect(x, y, self.slot_size, self.slot_size)

    def slot_index_at(self, pos):
        if not self.open or self.rect is None:
            return None
        ox, oy = self.grid_origin()
        for i in range(len(self.bags[0].slots)):
            if self.get_slot_rect(0, i, ox, oy).collidepoint(pos):
                return i
        return None

    def extra_content_height(self, scale):
        return 0
    
    def extra_content_top(self, scale):
        return 0

    def compute_panel_position(self, bg_width, bg_height, scale):
        """Centred, sliding left if the open inventory is in the way."""
        from content import inventory
        avoid = inventory.planned_rect() if inventory.open and inventory is not self else None
        return place_centre_window(bg_width, bg_height, avoid)

    def draw_extra_content(self, scale):
        pass

    def draw_slot_overlay(self, rect, item, bag_index, slot_index, scale):
        pass

    def on_slot_click(self, bag, bag_index, slot_index, drag_state):
        if drag_state.item is None:
            if bag.slots[slot_index] is not None:
                drag_state.item = bag.remove_item(slot_index)
                drag_state.source = (self.source_kind, bag_index, slot_index)
        else:
            existing = bag.slots[slot_index]
            bag.slots[slot_index] = drag_state.item
            drag_state.item = existing
            drag_state.source = (self.source_kind, bag_index, slot_index) if existing else None

        return True

    def draw(self):
        if not self.open:
            return

        scale = app.ui_scale
        self.slot_size = max(1, int(self.base_slot_size * scale))
        self.padding = max(1, int(self.base_padding * scale))
        self.panel_padding = max(1, int(16 * scale))
        self.row_extra = max(0, int(self.base_row_extra * scale))             

        slot_sprite = get_ui_scaled(self.slot_sprite_name, self.slot_size, self.slot_size)
        bag = self.bags[0]

        grid_width = bag.cols * (self.slot_size + self.padding) - self.padding
        grid_height = bag.rows * (self.slot_size + self.padding + self.row_extra) - self.padding

        top_h = self.extra_content_top(scale)
        extra_h = self.extra_content_height(scale)

        check_window_fits(self.window, grid_width + self.panel_padding * 2,
                          grid_height + self.panel_padding * 2 + extra_h + top_h)

        bg_width, bg_height = window_size(self.window)
        bg_x, bg_y = self.compute_panel_position(bg_width, bg_height, scale)
        self.rect = pygame.Rect(bg_x, bg_y, bg_width, bg_height)
        draw_window(self.window, self.rect)

        ox, oy = self.grid_origin()

        for bag_index, bag in enumerate(self.bags):
            for i, item in enumerate(bag.slots):
                rect = self.get_slot_rect(bag_index, i, ox, oy)
                app.screen.blit(slot_sprite, rect)
                if item:
                    item_sprite = scaled_sprites.get(item.sprite_name)
                    if item_sprite:
                        fitted = scale_item_sprite(item_sprite, self.slot_size * 0.9)
                        app.screen.blit(fitted, fitted.get_rect(center=rect.center))
                self.draw_slot_overlay(rect, item, bag_index, i, scale)
                if item and rect.collidepoint(pygame.mouse.get_pos()):
                    hover_state.item = item

        self.draw_extra_content(scale)

    def handle_click(self, pos, button, drag_state):
        if not self.open:
            return False
        ox, oy = self.grid_origin()
        for bag_index, bag in enumerate(self.bags):
            for i in range(len(bag.slots)):
                rect = self.get_slot_rect(bag_index, i, ox, oy)
                if rect.collidepoint(pos) and button == 1:
                    return self.on_slot_click(bag, bag_index, i, drag_state)
        if self.rect and self.rect.collidepoint(pos):
            return True 
        return False

class Inventory(GridContainer):
    source_kind = "inventory"
    window = "inventory"
    is_center_panel = False
    base_slot_size = inventory_slot_size
    base_padding = inventory_padding

    def __init__(self):
        super().__init__(inventory_collums, inventory_rows)
    
    def extra_content_top(self, scale):
        return int(4 * scale)     # no big header: the grid starts near the top

    def extra_content_height(self, scale):
        return int(28 * scale)   # room for the coin row

    def compute_panel_position(self, bg_width, bg_height, scale):
        return place_bottom_right_window(bg_width, bg_height)      # bottom-right corner, like before

    def planned_rect(self):
        """Where the inventory is (or would be) drawn, so other windows can make room for it."""
        w, h = window_size(self.window)
        return pygame.Rect(*place_bottom_right_window(w, h), w, h)

    def draw_extra_content(self, scale):
        self.draw_coin_counter(player.coins)

    def draw_coin_counter(self, coins):
        font_size = max(16, int(20 * (self.slot_size / inventory_slot_size)))
        font = get_font(font_size)
        text = font.render(f"Coins: {coins}", True, (255, 215, 0))
        text_x = self.rect.x + self.panel_padding
        text_y = self.rect.bottom - text.get_height() - self.panel_padding
        app.screen.blit(text, (text_x, text_y))

# --- Shop pricing -------------------------------------------------------------
shop_base_price = 50
shop_rarity_price_mult = {
    rarity_common:    1,
    rarity_uncommon:  2,
    rarity_rare:      4,
    rarity_epic:      8,
    rarity_legendary: 20,
}

def default_shop_price(item):
    mult = shop_rarity_price_mult.get(item.rarity, 1)
    return int(shop_base_price * mult)

class ShopStock:
    def __init__(self, random_entries=None, fixed=None, price_fn=None):
        self.random_entries = random_entries or []
        self.fixed = fixed or {}
        self.price_fn = price_fn or default_shop_price

    def roll_one_random(self):
        if not self.random_entries:
            return None
        weights = [e.weight for e in self.random_entries]
        if sum(weights) <= 0:
            return None
        entry = random.choices(self.random_entries, weights=weights, k=1)[0]
        return entry.item_factory()

    def roll(self, slot_count):
        items = [None] * slot_count
        prices = [0] * slot_count
        for i in range(slot_count):
            factory = self.fixed.get(i)
            item = factory() if factory is not None else self.roll_one_random()
            if item is not None:
                items[i] = item
                prices[i] = self.price_fn(item)
        return items, prices

#Shop container
shop_containers = []
shops = {}   

def register_shop(name, shop):
    shop.name = name
    shops[name] = shop
    return shop

class ShopContainer(GridContainer):
    source_kind = "shop"
    window = "shop"
    base_row_extra = 20   

    def __init__(self, cols, rows, stock=None, reroll_cost=100):
        super().__init__(cols, rows)
        self.prices = [0] * (cols * rows)
        self.stock = stock
        self.reroll_cost = reroll_cost
        self.reroll_rect = None
        self.name = None
        self.stocked = False        
        shop_containers.append(self)

    def generate_stock(self):
        if self.stock is None:
            return
        items, prices = self.stock.roll(len(self.bags[0].slots))
        self.bags[0].slots = items
        self.prices = prices
        self.stocked = True

    def ensure_stocked(self):
        if self.stocked:
            return
        self.generate_stock()

    def reroll(self):
        if player.coins < self.reroll_cost:
            return
        player.coins -= self.reroll_cost
        self.generate_stock()

    def on_slot_click(self, bag, bag_index, slot_index, drag_state):
        from content.shops import inventory
        if drag_state.item is not None:
            return True
        item = bag.slots[slot_index]
        if item is None:
            return True
        price = self.prices[slot_index]
        if player.coins >= price:
            if inventory.bags[0].add_item(item):  
                player.coins -= price
                bag.slots[slot_index] = None
                self.prices[slot_index] = 0
        return True

    def draw_slot_overlay(self, rect, item, bag_index, slot_index, scale):
        if item is None:
            return
        price = self.prices[slot_index]
        font = get_font(max(12, int(18 * scale)))
        text = font.render(f"{price}G", True, (255, 215, 0))
        text_rect = text.get_rect(center=(rect.centerx, rect.bottom + int(self.row_extra * 0.55)))
        app.screen.blit(text, text_rect)

    def extra_content_height(self, scale):
        return int(52 * scale)   

    def draw_extra_content(self, scale):
        btn_w = int(180 * scale)
        btn_h = int(38 * scale)
        x = self.rect.centerx - btn_w // 2
        y = self.rect.bottom - self.panel_padding - btn_h
        self.reroll_rect = pygame.Rect(x, y, btn_w, btn_h)

        affordable = player.coins >= self.reroll_cost
        fill = (70, 70, 95) if affordable else (45, 45, 50)
        pygame.draw.rect(app.screen, fill, self.reroll_rect, border_radius=6)
        pygame.draw.rect(app.screen, (200, 200, 220), self.reroll_rect, width=2, border_radius=6)

        font = get_font(max(14, int(20 * scale)))
        label = font.render(f"Reroll ({self.reroll_cost}G)", True, (255, 215, 0) if affordable else (150, 150, 150))
        app.screen.blit(label, label.get_rect(center=self.reroll_rect.center))

    def handle_click(self, pos, button, drag_state):
        if not self.open:
            return False
        if button == 1 and self.reroll_rect and self.reroll_rect.collidepoint(pos):
            self.reroll()
            return True
        return super().handle_click(pos, button, drag_state)
