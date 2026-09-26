import pygame
from core.state import app, world
from core.screen import camera
from core.assets import sprite_rects, update_screen_data
from systems.items import drag_state, equipment
from systems.melee import melee_swings
from systems.ground import assign_label_slots, drop_item_on_ground, try_pickup_ground_item_click, try_pickup_ground_label_click
from systems.player import player
from systems.areas import areas, switch_area, try_click_portal
from ui.widgets import Dropdown, buttons, loot_filter_checkbox, loot_filter_dropdown, menu_buttons
from ui.panels import attack_blocking_panel_open, grid_containers, open_center_panel
from ui.chest import try_click_container_object, try_shift_transfer


# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Game state and events

def handle_events():
    
    from content import inventory
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit_game()
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and app.game_state != "menu":
                if Dropdown.close_open():
                    pass
                elif app.game_state == "settings":
                    toggle_settings()
                elif equipment.open or any(c.open for c in grid_containers):
                    equipment.open = False
                    for c in grid_containers:
                        c.open = False
                else:
                    toggle_settings()
        
            elif event.key == pygame.K_i:
                if app.game_state == "":
                    inventory.toggle()

            elif event.key == pygame.K_e:
                if app.game_state == "":
                    if equipment.open:
                        open_center_panel(None)
                    else:
                        open_center_panel(equipment)

            elif event.key == pygame.K_SPACE:
                if app.game_state == "":
                    player.use_dash()
            
            elif event.key == pygame.K_z:
                app.show_all_labels = not app.show_all_labels
                if app.show_all_labels:
                    assign_label_slots()
            
            elif event.key == pygame.K_q:
                app.debug_hitboxes = not app.debug_hitboxes

        elif event.type == pygame.MOUSEBUTTONDOWN:
            handle_mouse(event.pos, event.button)
        
#Button actions 
def handle_mouse(pos, button):

    from systems.save import save_game
    app.attack_input_blocked = True 

    if app.game_state == "settings":
        if loot_filter_dropdown.handle_click(pos):
            return
        if loot_filter_checkbox.handle_click(pos):
            return
        
        for b in buttons:
            if b.rect.collidepoint(pos):

                if b.action == "toggle_fullscreen":
                    toggle_fullscreen()

                elif b.action == "quit":
                    quit_game()

                elif b.action == "save_exit":
                    save_game()
                    toggle_settings()
                
                elif b.action == "restart":
                    restart_game()

                elif b.action == "menu":
                    Dropdown.close_open()
                    app.game_state = "menu"
        return

    if app.game_state == "menu":
        for b in menu_buttons:
            if b.rect.collidepoint(pos):

                if b.action == "play":
                    app.game_state = ""

                elif b.action == "quit":
                    quit_game()

                elif b.action == "settings":
                    toggle_settings()
        return

    if sprite_rects["gear_sprite"].collidepoint(pos):
        toggle_settings()
        return
    
    if button == 1:
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_SHIFT and drag_state.item is None:
            if try_shift_transfer(pos):
                return

        if equipment.handle_click(pos, button, drag_state, player):
            return
        for c in grid_containers:
            if c.handle_click(pos, button, drag_state):
                return

        if drag_state.item is not None:
            drop_item_on_ground(drag_state.item, player)
            drag_state.item = None
            drag_state.source = None
            return

        for rect in app.hotbar_rects.values():
            if rect.collidepoint(pos):
                return

        if try_pickup_ground_label_click(pos, player):
            return
        if try_pickup_ground_item_click(pos, player):
            return
        if try_click_container_object(pos):
            return
        if try_click_portal(pos):
            return
        if attack_blocking_panel_open():
            return
        
        app.attack_input_blocked = False
        player.use_ability("primary", pos, camera)

app.previous_game_state = "menu"
app.attack_input_blocked = False
app.debug_hitboxes = False

def toggle_settings():

    if app.game_state == "settings":
        Dropdown.close_open()
        app.game_state = app.previous_game_state
    else:
        app.previous_game_state = app.game_state
        app.game_state = "settings"
    
def quit_game():
    app.running = False

def toggle_fullscreen():
    
    if app.fullscreen:
        app.screen = pygame.display.set_mode((1200,1000))
    else:
        app.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    app.fullscreen = not app.fullscreen
    app.screen_width, app.screen_height = app.screen.get_size()
    update_screen_data()
    
    for b in buttons:
            b.update()
    
def restart_game():

    app.start_completed = True

    for name, area in areas.items():
        if name == "start":
            continue
        area.generated = False
        area.world_objects = []
        area.enemies = []
        area.ground_items = []
        area.portals = []

    world.ground_items.clear()
    world.projectiles.clear()
    world.enemy_projectiles.clear()
    melee_swings.clear()

    switch_area(areas["home"])
    app.game_state = ""

