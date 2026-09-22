import pygame
import random
from core.state import app, world
from core.screen import get_font
from core.assets import scaled_sprites
from systems.rarity import rarity_colors, rarity_common, rarity_epic, rarity_legendary, rarity_order, rarity_rare, rarity_uncommon, unique_color
from systems.items import item_category_currency
from systems.drops import generic_drop_pool

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Ground items

world.ground_items = []
app.ground_label_rects = []

loot_filter_levels = [rarity_common, rarity_uncommon, rarity_rare, rarity_epic, rarity_legendary]
app.loot_filter_index = 0
app.loot_filter_enabled = False

app.show_all_labels = False
app.label_font = None
app.label_row_h = 0
label_pad_x = 8       # box padding left/right (bigger boxes)
label_pad_y = 4       # box padding top/bottom
cluster_radius = 100  # world distance: items closer than this share a grid

def get_label_font():
    if app.label_font is None:
        scale = app.ui_scale
        app.label_font = get_font(max(14, int(18 * scale)))
        app.label_row_h = app.label_font.get_height() + label_pad_y * 2
    return app.label_font

def label_box_width(g):
    font = get_label_font()
    w = font.render(ground_label_text(g), True, (255, 255, 255)).get_width() + label_pad_x * 2
    if getattr(g.item, "built_in_support", None) is not None:
        w += font.get_height() + 2     
    return w

def ground_label_text(g):
    if g.item.category == item_category_currency:
        return f"{g.stack_count} Gold"
    return g.item.name

def ground_label_color(g):
    if g.item.category == item_category_currency:
        return (255, 215, 0)
    if getattr(g.item, "is_unique", False):
        return unique_color
    return rarity_colors.get(g.item.rarity, (255, 255, 255))

def assign_label_slots():
    get_label_font()
    items = [g for g in world.ground_items if item_passes_filter(g.item)]     
    for g in items:
        g.label_offset = None

    if not items:
        return

    clusters = [] 
    r2 = cluster_radius * cluster_radius
    for g in items:
        placed = False
        for c in clusters:
            dx = g.x - c["cx"]
            dy = g.y - c["cy"]
            if dx * dx + dy * dy <= r2:
                c["items"].append(g)
                n = len(c["items"])
                c["cx"] += (g.x - c["cx"]) / n
                c["cy"] += (g.y - c["cy"]) / n
                placed = True
                break
        if not placed:
            clusters.append({"cx": g.x, "cy": g.y, "items": [g]})

    h = app.label_row_h

    for c in clusters:
        cluster_items = c["items"]
        n = len(cluster_items)
        start = -(n - 1) / 2
        for i, g in enumerate(cluster_items):
            row_offset = start + i
            g.label_offset = (0, row_offset * h)  
            g.label_anchor = (c["cx"], c["cy"])
            g.label_col_w = label_box_width(g)      

def loot_filter_min_rarity():
    return loot_filter_levels[app.loot_filter_index]

def item_passes_filter(item):
    if not app.loot_filter_enabled:
        return True
    if item.category == item_category_currency:
        return True
    if getattr(item, "built_in_support", None) is not None:
        return True
    return rarity_order.index(item.rarity) >= app.loot_filter_index

class GroundItem:
    def __init__(self, item, x, y):
        self.item = item
        self.x = x
        self.y = y
        self.stack_count = 1
        sprite = scaled_sprites.get(item.sprite_name)
        self.rect = sprite.get_rect() if sprite else pygame.Rect(0, 0, 0, 0)
        self.label_offset = None
        self.label_anchor = None
        self.label_col_w = 0

    def ground_item_update_hitbox(self, camera):
        sprite = scaled_sprites.get(self.item.sprite_name)
        if sprite:
            self.rect = sprite.get_rect(center=camera.apply_camera(self.x, self.y))
    
    def ground_item_draw(self):
        if not item_passes_filter(self.item):
            return
        sprite = scaled_sprites.get(self.item.sprite_name)
        if sprite:
            app.screen.blit(sprite, self.rect)

coin_stack_cell_size = 256     

def ground_cell(x, y):
    return (int(x // coin_stack_cell_size), int(y // coin_stack_cell_size))

def add_ground_item(item, x, y):
    if item.category == item_category_currency:
        cell = ground_cell(x, y)
        for g in world.ground_items:
            if (g.item.category == item_category_currency
                    and g.item.name == item.name
                    and ground_cell(g.x, g.y) == cell):
                g.stack_count += 1
                return g
    g = GroundItem(item, x, y)
    world.ground_items.append(g)
    return g

def spawn_drops(enemy):
    dropped = []
    if not enemy.skip_generic_drops:
        dropped += generic_drop_pool.roll()
    dropped += enemy.drop_pool.roll()
    for factory in enemy.guaranteed_drops:
        dropped.append(factory())
    for item in dropped:
        offset_x = random.randint(-15, 15)
        offset_y = random.randint(-15, 15)
        add_ground_item(item, enemy.x + offset_x, enemy.y + offset_y)      
    assign_label_slots()

coin_pickup_radius = 50

def try_pickup_coins(player):
    remaining = []
    for g in world.ground_items:
        if g.item.category == item_category_currency:
            dx = g.x - player.x
            dy = g.y - player.y
            distance = (dx * dx + dy * dy) ** 0.5
            if distance <= coin_pickup_radius:
                player.coins += g.stack_count
                continue
        remaining.append(g)
    world.ground_items = remaining

pickup_click_radius = 60
click_target_tolerance = 30

def try_pickup_ground_label_click(pos, player):
    from content import inventory
    for rect, g in app.ground_label_rects:
        if g not in world.ground_items:
            continue
        if rect.collidepoint(pos):
            player_dx = g.x - player.x
            player_dy = g.y - player.y
            player_distance = (player_dx * player_dx + player_dy * player_dy) ** 0.5

            if g.item.category == item_category_currency:
                player.move_target = make_pickup_order(g)
                return True

            if player_distance <= pickup_click_radius:
                if inventory.bags[0].add_item(g.item):
                    world.ground_items.remove(g)
            else:
                player.move_target = make_pickup_order(g)
            return True
    return False

def try_pickup_ground_item_click(pos, player):
    from content import inventory
    for g in world.ground_items:
        if g.item.category == item_category_currency or not g.rect:
            continue
        if not item_passes_filter(g.item):
            continue

        click_dx = pos[0] - g.rect.centerx
        click_dy = pos[1] - g.rect.centery
        click_distance = (click_dx * click_dx + click_dy * click_dy) ** 0.5

        if click_distance <= click_target_tolerance:
            player_dx = g.x - player.x
            player_dy = g.y - player.y
            player_distance = (player_dx * player_dx + player_dy * player_dy) ** 0.5

            if player_distance <= pickup_click_radius:
                if inventory.bags[0].add_item(g.item):
                    world.ground_items.remove(g)
            else:
                player.move_target = make_pickup_order(g)
            return True
    return False

def make_pickup_order(g):
    from systems.player import MoveOrder
    from content import inventory
    def on_arrive():
        if g.item.category != item_category_currency:
            if inventory.bags[0].add_item(g.item):
                world.ground_items.remove(g)
    return MoveOrder(g, pickup_click_radius, on_arrive, is_valid=lambda: g in world.ground_items)

def drop_item_on_ground(item, player):
    offset_x = random.randint(-20, 20)
    offset_y = random.randint(-20, 20)
    add_ground_item(item, player.x + offset_x, player.y + offset_y)
    assign_label_slots()
