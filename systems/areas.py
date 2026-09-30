import pygame
import random
from core.state import app, world
from systems.melee import melee_swings
from systems.abilities import pending_bursts
from systems.player import MoveOrder, player
from systems.world_objects import WorldObject, formation_shapes, nearest_free_point, world_rect_at
from systems.enemies import Enemy
from systems.packs import (PackPool, apply_enemy_tier, pack_configs, roll_enemy_level, roll_enemy_tier, spot_pickers)

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
    def __init__(self, name, width, height, spawn, tile="grass_tile_sprite", build=None, level=1,
                 persistent=True):
        self.name = name
        self.level = level        # monsters and (later) loot are built from this
        # persistent=True   built once; kills, drops and changes stay until restart
        # persistent=False  rebuilt every time you walk in; dropped loot is lost
        self.persistent = persistent
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
        self.reserved = []        # [(x, y, radius)] - kept clear of RANDOM scenery
        self.scattering = False   # True while scatter/formations are running

    def reset(self):
        """Forget everything here - scenery, monsters and items on the ground.
        The area is built again from scratch next time it is entered."""
        self.world_objects = []
        self.enemies = []
        self.ground_items = []
        self.portals = []
        self.reserved = []
        self.generated = False

    def reserve(self, x, y, radius=140):
        """Keep this circle clear of anything that blocks movement.
        The spawn point and every portal reserve themselves automatically."""
        self.reserved.append((x, y, radius))

    def is_reserved(self, x, y, gap=0):
        return any((x - rx) ** 2 + (y - ry) ** 2 < (r + gap) ** 2 for rx, ry, r in self.reserved)

    def add(self, object_type, x, y, container=None):
        """One world object. `container` links a chest / shop to its inventory.
        An object you place by hand is ALWAYS placed - reserved ground only
        keeps random scenery away."""
        obj = WorldObject(x, y, object_type)
        if container is not None:
            obj.linked_container = container
        obj.is_scenery = self.scattering
        self.world_objects.append(obj)
        return obj

    def add_enemy(self, enemy_type, x, y, **extra):
        enemy = Enemy(x, y, enemy_type)
        for key, value in extra.items():
            setattr(enemy, key, value)
        self.enemies.append(enemy)
        return enemy

    def portal(self, x, y, target_area, spawn=None):
        self.reserve(x, y, area_portal_clearance)
        self.tidy_reserved()                # scenery built here earlier moves aside
        self.portals.append(Portal(x, y, target_area, target_spawn=spawn))

    # --- shapes -----------------------------------------------------
    def border(self, object_type, spacing=64, margin=40):
        """A wall of `object_type` right round the edge. Follows the map size."""
        x = margin
        while x <= self.width - margin:
            self.add(object_type, x, margin)
            self.add(object_type, x, self.height - margin)
            x += spacing
        y = margin
        while y <= self.height - margin:
            self.add(object_type, margin, y)
            self.add(object_type, self.width - margin, y)
            y += spacing

    def line(self, object_type, start, end, spacing=64):
        """A row of objects from start=(x, y) to end=(x, y)."""
        x1, y1 = start
        x2, y2 = end
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        steps = max(1, int(length // spacing))
        for i in range(steps + 1):
            t = i / steps
            self.add(object_type, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)

    def formation(self, shape, object_type, x, y, **settings):
        """One shape (cluster, ring, vein, clump...) centred on (x, y)."""
        formation_shapes[shape](self, object_type, x, y, **settings)

    def scatter_formations(self, shape, object_type, amount, bounds=None, gap=300, **settings):
        """`amount` copies of a shape, spread out so they don't sit on each other.
        Extra settings (count, radius...) are passed on to the shape itself."""
        spots = self.free_spots(amount, bounds, gap)
        self.scattering = True
        for x, y in spots:
            self.formation(shape, object_type, x, y, **settings)
        self.scattering = False
        self.tidy_reserved()

    def scatter(self, object_type, amount, bounds=None, gap=80):
        """`amount` single objects dropped at random, never on top of each other."""
        spots = self.free_spots(amount, bounds, gap)
        self.scattering = True
        for x, y in spots:
            self.add(object_type, x, y)
        self.scattering = False
        self.tidy_reserved()

    def tidy_reserved(self):
        """Drop random scenery that spilled onto reserved ground.
        Objects you placed by hand are never touched."""
        keep = []
        for o in self.world_objects:
            if (getattr(o, "is_scenery", False) and o.blocks_movement
                    and self.is_reserved(o.x, o.y, gap=o.rect.width / 2)):
                continue
            keep.append(o)
        self.world_objects = keep

    # --- finding room ------------------------------------------------
    def free_spots(self, amount, bounds=None, gap=120, spacing=None, tries_each=30, min_gap=None):
        """Up to `amount` points to build something on.

        gap      how much clear room each point needs.
        min_gap  how far `gap` may shrink on a tight map. Leave it out and gap
                    never shrinks, so nothing you build lands inside a rock.
        spacing  how far apart the points should be. Always relaxed if needed.
        """
        if bounds is None:
            inset = max(gap, 150)
            bounds = (inset, inset, self.width - inset, self.height - inset)
        if spacing is None:
            spacing = gap * 2
        left, top, right, bottom = bounds
        if right <= left or bottom <= top:
            return []

        taken = [world_rect_at(o) for o in self.world_objects if o.blocks_movement]
        spots = []
        for _ in range(4):                       # each round is less fussy than the last
            if len(spots) >= amount:
                break
            if min_gap is not None:
                gap = max(min_gap, gap * 0.6)
            for _ in range(amount - len(spots)):
                for _ in range(tries_each):
                    x = random.uniform(left, right)
                    y = random.uniform(top, bottom)
                    box = pygame.Rect(x - gap, y - gap, gap * 2, gap * 2)
                    if any(r.colliderect(box) for r in taken):
                        continue
                    if self.is_reserved(x, y, gap):
                        continue
                    if any((x - sx) ** 2 + (y - sy) ** 2 < spacing ** 2 for sx, sy in spots):
                        continue
                    spots.append((x, y))
                    break
            spacing *= 0.5
        return spots

    def is_free(self, x, y, gap=40):
        box = pygame.Rect(x - gap, y - gap, gap * 2, gap * 2)
        return not any(world_rect_at(o).colliderect(box)
                       for o in self.world_objects if o.blocks_movement)

    # --- monster packs -----------------------------------------------
    def spawn_packs(self, pool, count, spots=None, picker="random", gap=250):
        """Spawn packs from `pool`. THE AREA decides how many.

        pool   a PackPool, or just a list of pack names
        count  how many packs: a number, or (min, max) to roll between
        spots  your own list of (x, y); leave out and it finds open ground
        picker how the spots are chosen - "random" for now, see systems/packs.py

        Every monster gets .level and .tier from this area's level.
        """
        if not isinstance(pool, PackPool):
            pool = PackPool([(name, 1) for name in pool])
        if isinstance(count, (tuple, list)):
            count = random.randint(count[0], count[1])
        if count <= 0:
            return
        if spots is None:
            # packs may squeeze closer to the scenery than decoration may,
            # because every member is checked on its own below
            spots = self.free_spots(count * 2, gap=gap, min_gap=70)
        chosen = spot_pickers[picker](list(spots), count, self)
        for x, y in chosen:
            name = pool.roll()
            if name is None:
                continue
            for enemy_type, ox, oy, entry in pack_configs[name].roll():
                ex, ey = x + ox, y + oy
                if not self.is_free(ex, ey):
                    ex, ey = x, y                 # fall back to the pack's centre
                enemy = self.add_enemy(
                    enemy_type, ex, ey,
                    level=roll_enemy_level(self.level, entry),
                    tier=roll_enemy_tier(self.level, entry),
                    pack=name,
                    **entry.extra)
                apply_enemy_tier(enemy)

areas = {}
world.current_area = None
app.start_completed = False
portal_use_radius = 60
area_spawn_clearance = 160    # clear room kept around an area's spawn point
area_portal_clearance = 140   # clear room kept around every portal

def register_area(area):
    areas[area.name] = area

def switch_area(target, spawn_pos=None):

    if world.current_area is not None and world.current_area.name == "start":
        app.start_completed = True

    if world.current_area is not None:
        leaving = world.current_area
        leaving.world_objects = world.world_objects
        leaving.enemies = world.enemies
        leaving.ground_items = world.ground_items
        if not leaving.persistent:
            leaving.reset()          # nothing here survives being left

    if not target.persistent:
        target.reset()               # always walk into a fresh one

    if not target.generated:
        if target.build:
            target.world_objects = []
            target.enemies = []
            target.portals = []
            target.reserved = []
            target.reserve(target.spawn[0], target.spawn[1], area_spawn_clearance)
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
    # last safety net: never drop the player inside something solid
    player.x, player.y = nearest_free_point(target.width / 2, target.height / 2, spawn_pos[0], spawn_pos[1], 20)
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
