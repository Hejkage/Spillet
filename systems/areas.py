import pygame
from core.state import app, world
from systems.melee import melee_swings
from systems.abilities import pending_bursts
from systems.player import MoveOrder, player

# region Areas / maps

class Portal:
    def __init__(self, x, y, target_area, target_spawn=None, size=(64, 64)):
        self.x = x
        self.y = y
        self.target_area = target_area
        self.target_spawn = target_spawn
        self.width, self.height = size
        self.rect = pygame.Rect(0, 0, self.width, self.height)

    def world_rect(self):
        return pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
    
    def portal_update_hitbox(self, camera):
        self.rect = self.world_rect()
        self.rect.center = camera.apply_camera(self.x, self.y)

    def portal_draw(self):
        pygame.draw.rect(app.screen, (150, 80, 220), self.rect, border_radius=8)
        pygame.draw.rect(app.screen, (230, 200, 255), self.rect, width=3, border_radius=8)

class Area:
    def __init__(self, name, width, height, spawn, tile="grass_tile_sprite", build=None):
        self.name = name
        self.width = width
        self.height = height
        self.spawn = spawn
        self.tile = tile
        self.build = build
        self.generated = False
        self.world_objects = []
        self.enemies = []
        self.ground_items = []
        self.portals = []

areas = {}
world.current_area = None
app.start_completed = False
portal_use_radius = 60

def register_area(area):
    areas[area.name] = area

def switch_area(target, spawn_pos=None):

    if world.current_area is not None and world.current_area.name == "start":
        app.start_completed = True

    if world.current_area is not None:
        world.current_area.world_objects = world.world_objects
        world.current_area.enemies = world.enemies
        world.current_area.ground_items = world.ground_items

    if not target.generated:
        if target.build:
            target.build(target)
        target.generated = True

    world.current_area = target

    world.world_objects = target.world_objects
    world.enemies = target.enemies
    world.ground_items = target.ground_items
    world.width = target.width
    world.height = target.height
    world.projectiles = []
    world.enemy_projectiles = []
    pending_bursts.clear()
    melee_swings.clear()

    if spawn_pos is None:
        spawn_pos = target.spawn
    player.x, player.y = spawn_pos
    player.move_target = None
    for pet in player.pets:
        pet.x, pet.y = player.x, player.y

def try_click_portal(pos):
    for portal in world.current_area.portals:
        if portal.rect.collidepoint(pos):
            player.move_target = make_portal_order(portal)
            return True
    return False

def make_portal_order(portal):
    def on_arrive():
        switch_area(areas[portal.target_area], portal.target_spawn)
    return MoveOrder(portal, portal_use_radius, on_arrive, is_valid=lambda: world.current_area is not None and portal in world.current_area.portals)
