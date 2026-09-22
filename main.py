import pygame
from core.state import app, world
from core.screen import camera
from core.assets import draw_background, draw_sprite, scaled_sprites, update_screen_data
from systems.projectiles import update_orbit_ring
from systems.items import draw_all_ground_labels, draw_dragged_item, draw_ground_item_label, draw_item_tooltip, equipment, hover_state
from systems.melee import draw_melee_swings, update_melee_swings
from systems.abilities import pending_bursts
from systems.world_objects import draw_depth_sorted
from systems.ground import item_passes_filter, try_pickup_coins
from systems.player import player
from systems.enemies import enemy_grid, process_projectile_hits
from systems.areas import areas, switch_area
from ui.widgets import buttons, loot_filter_checkbox, loot_filter_dropdown, menu_buttons
from ui.panels import attack_blocking_panel_open, grid_containers, shop_containers
from ui.hotbar import ability_keybinds, draw_ability_tooltip, draw_hotbar
from ui.menus import draw_fps, draw_health_bar, draw_main_menu, draw_settings_menu, draw_xp_bar
from core.events import handle_events
from systems.save import load_game
from content import inventory

# region Main game loop

app.fullscreen = True
app.game_state = "menu"
app.running = True
clock = pygame.time.Clock()

def update_player_input(dt):
    if pygame.mouse.get_pressed()[0] and not app.attack_input_blocked and not attack_blocking_panel_open():
        player.use_ability("primary", pygame.mouse.get_pos(), camera)
    if not attack_blocking_panel_open():
        held_keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        for slot, key in ability_keybinds.items():
            if held_keys[key]:
                player.use_ability(slot, mouse_pos, camera)

def update_projectiles(dt):
    for pb in pending_bursts:
        pb.update(dt)
    pending_bursts[:] = [pb for pb in pending_bursts if pb.remaining > 0]
    update_orbit_ring(dt)
    for p in world.projectiles:
        p.projectile_update(dt, camera)
    world.projectiles = [p for p in world.projectiles if p.alive]
    for p in world.enemy_projectiles:
        p.projectile_update(dt, camera)
        if p.alive and p.hits_player(player):
            player.take_damage(p.damage)
            p.alive = False
    world.enemy_projectiles[:] = [p for p in world.enemy_projectiles if p.alive]
    process_projectile_hits(world.projectiles)

def update_enemies(dt):
    enemy_grid.rebuild(world.enemies)
    for e in world.enemies:
        e.update_ai(player, dt)
        e.update_statuses(dt)
        e.enemy_update_hitbox(camera)
    world.enemies = [e for e in world.enemies if e.alive]

def update_world(dt):
    for g in world.ground_items:
        g.ground_item_update_hitbox(camera)
        if (not app.show_all_labels and not inventory.open and not equipment.open
                and item_passes_filter(g.item) and g.rect.collidepoint(pygame.mouse.get_pos())):
            hover_state.ground_item = g
    for o in world.world_objects:
        o.world_object_update_hitbox(camera)
    try_pickup_coins(player)

update_systems = []   # list of (order, fn(dt))
draw_layers    = []   # list of (order, fn())

def register_update(order, fn):
    update_systems.append((order, fn))
    update_systems.sort(key=lambda p: p[0])

def register_draw(order, fn):
    draw_layers.append((order, fn))
    draw_layers.sort(key=lambda p: p[0])

register_update(10, lambda dt: player.move(dt))
register_update(20, update_player_input)
register_update(25, lambda dt: player.update_abilities(dt))
register_update(26, lambda dt: player.update_health(dt))
register_update(27, lambda dt: camera.camera_update(player))
register_update(28, lambda dt: [pet.pet_update(player, dt) for pet in player.pets])
register_update(30, update_projectiles)
register_update(35, update_melee_swings)   # update_melee_swings already takes dt
register_update(40, update_enemies)
register_update(50, update_world)

update_screen_data()

load_game()
for shop in shop_containers:
    shop.ensure_stocked()
if app.start_completed:
    switch_area(areas["home"])
else:
    switch_area(areas["start"])

while app.running:
    dt = clock.tick(60) / 1000
    handle_events()
    app.screen.fill((30, 30, 30))
    hover_state.item = None
    hover_state.ability = None
    hover_state.ground_item = None

#update
    if app.game_state == "menu" or (app.game_state == "settings" and app.previous_game_state == "menu"):
        draw_main_menu()

        for b in menu_buttons:
            b.draw_button()

    elif app.game_state == "" or (app.game_state == "settings" and app.previous_game_state == ""): 
        
        player.recalculate_stats()
        player.rebuild_basic_attack()
        player.rebuild_gem_ability()
        player.rebuild_pets()

    #Game function stuff
        if app.game_state != "settings":
            for _, fn in update_systems:
                fn(dt)
    #Drawing
        draw_background()

        for portal in world.current_area.portals:
            portal.portal_update_hitbox(camera)
            portal.portal_draw()
        
        for g in world.ground_items:
            g.ground_item_draw()

        for p in world.projectiles:
            p.projectile_draw(camera)

        for p in world.enemy_projectiles:
            p.projectile_draw(camera)

        depth_entities = [(o, o.world_object_draw) for o in world.world_objects]
        depth_entities.append((player, lambda: player.draw_player(camera)))
        for pet in player.pets:
            depth_entities.append((pet, lambda pet=pet: pet.draw_pet(camera)))

        for e in world.enemies:
            if e.enemy_is_on_screen(camera):
                depth_entities.append((e, e.enemy_draw))
        draw_depth_sorted(depth_entities)

        draw_melee_swings(camera)

        draw_sprite("gear_sprite")
        draw_xp_bar(player)
        draw_health_bar(player)
        draw_hotbar(player)

    if app.game_state == "settings" and app.previous_game_state != "menu":
        draw_settings_menu()

    if app.game_state == "settings":
        for b in buttons:
            b.draw_button()
        loot_filter_dropdown.draw()
        loot_filter_checkbox.draw()
    
    draw_all_ground_labels()
    draw_ground_item_label()
    for c in grid_containers:
        c.draw()
    equipment.draw(scaled_sprites, player)
    draw_dragged_item()
    draw_item_tooltip()
    draw_ability_tooltip(player)

    draw_fps(clock)
    
    #Flip
    pygame.display.flip()

pygame.quit()
