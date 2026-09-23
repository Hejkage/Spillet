import pygame
import random
from core.state import app, world
from core.assets import scaled_sprites
from systems.weapons import weapon_class_tags
from systems.supports import support_gem_types
from systems.items import active_gem_slot, equipment, pet_equip_slots, stat_defs, support_gem_slots
from systems.abilities import active_gem_templates, basic_attacks_by_weapon, build_active_gem
from systems.world_objects import world_rect_at
from systems.pets import Pet
from core.screen import camera

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Player
class MoveOrder:
    def __init__(self, target, radius, on_arrive, is_valid=None):
        self.target = target                   
        self.radius = radius                    
        self.on_arrive = on_arrive            
        self.is_valid = is_valid or (lambda: True)  

class Player:
    def __init__(self, sprite_name, player_x, player_y):
        self.sprite_name = sprite_name
        self.x = player_x
        self.y = player_y
        self.facing = 1
        self.coins = 0
        self.xp = 0
        self.level = 1
        self.xp_to_next_level = 100
        self.move_target = None
        self.abilities = {
            "primary": None,
            "main": None
        }
        self.basic_attack_signature = object()
        self.gem_signature = None
        self.pets = []
        self.pet_signature = None
    #Dash stats
        self.dash_speed_multiplier = 4
        self.dash_duration = 0.15
        self.dash_cooldown = 0.6
        self.dash_timer = 0
        self.dash_time_remaining = 0
        self.dash_direction = pygame.Vector2(0, 0)
        self.action_lock_timer = 0.0
        self.action_timers = {}
        self.stats_dirty = True

        self.base_stats   = {k: d["base"] for k, d in stat_defs.items()}
        self.added_flat = {stat: 0 for stat in self.base_stats}
        self.increased = {stat: 0 for stat in self.base_stats}
        self.more_multipliers = {stat: 1 for stat in self.base_stats}

        self.recalculate_stats()
        self.current_health = self.max_health

    def try_dash(self):
        if self.dash_timer > 0:
            return
        
        mouse_pos = pygame.mouse.get_pos()
        player_screen_pos = pygame.Vector2(camera.apply_camera(self.x, self.y))
        direction = pygame.Vector2(mouse_pos) - player_screen_pos
        
        if direction.length() > 0:
            self.dash_direction = direction.normalize()
            self.dash_time_remaining = self.dash_duration
            self.dash_timer = self.dash_cooldown
            self.action_lock_timer = 0
    
    def use_dash(self):
        self.try_dash()

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = int(self.xp_to_next_level * 1.25)

    def take_damage(self, amount):
        if self.current_health <= 0:
            return
        self.current_health -= amount
        if self.current_health <= 0:
            self.current_health = 0
            self.die()
    
    def heal(self, amount):
        self.current_health = min(self.max_health, self.current_health + amount)

    def die(self):
        from systems.areas import areas, switch_area
        self.current_health = self.max_health
        switch_area(areas["home"])
    
    def update_health(self, dt):
        if self.health_regen > 0 and self.current_health > 0:
            self.heal(self.health_regen * dt)
    
    def resolve_stat(self, key, hit_stats=None):
        s = hit_stats or {}
        flat = self.base_stats[key] + self.added_flat[key] + s.get(key, 0)
        inc  = 1 + self.increased[key] + s.get(key + "_increase", 0) / 100
        more = self.more_multipliers[key] * s.get(key + "_more", 1.0)
        return flat * inc * more

    def crit_stats(self, hit_stats=None):
        return (self.resolve_stat("crit_chance", hit_stats),
                self.resolve_stat("crit_damage", hit_stats))

    def recalculate_stats(self, force=False):
        signature = tuple(id(i) if i else None for i in list(equipment.main_slots.values()) + list(equipment.extra_slots.values()))
        if not force and signature == getattr(self, "_stat_signature", None):
            return
        self._stat_signature = signature

        for stat in self.base_stats:
            self.added_flat[stat] = 0
            self.increased[stat] = 0
            self.more_multipliers[stat] = 1.0

        for item in list(equipment.main_slots.values()) + list(equipment.extra_slots.values()):
            if not item:
                continue
            for mod in item.stats.values():
                self.apply_modifier(mod)

        for stat in self.base_stats:
            setattr(self, stat, self.resolve_stat(stat))

        if hasattr(self, "current_health"):
            self.current_health = min(self.current_health, self.max_health)

    def rebuild_basic_attack(self):
        weapon_class = self.equipped_weapon_class()
        if weapon_class == self.basic_attack_signature:
            return
        self.basic_attack_signature = weapon_class

        self.abilities["primary"] = basic_attacks_by_weapon.get(
            weapon_class, basic_attacks_by_weapon[None]
        )

    def rebuild_gem_ability(self):
        active_item = equipment.extra_slots.get(active_gem_slot)
        supports = [equipment.extra_slots[s].support_gem for s in support_gem_slots if equipment.extra_slots[s] is not None]

        built_in = getattr(active_item, "built_in_support", None) if active_item else None
        if built_in is not None:
            supports = [built_in] + supports

        signature = (id(active_item), tuple(id(s) for s in supports))
        if signature == self.gem_signature:
            return
        self.gem_signature = signature

        if active_item is None:
            self.abilities["main"] = None
            return

        t = active_gem_templates[active_item.template_key]
        allowed_tags = t.get("support_tags", set())
        supports = [s for s in supports if support_gem_types[s.gem_type]["tags"] & allowed_tags]

        gem_stats = getattr(active_item, "gem_stats", None)
        self.abilities["main"] = build_active_gem(t, supports, gem_stats=gem_stats)

    def rebuild_pets(self):
        equipped = [equipment.pet_slots[s] for s in pet_equip_slots]

        weapon = equipment.main_slots.get("weapon")
        summon_types = getattr(weapon, "summon_pets", []) if weapon else []

        signature = (
            tuple(id(item) if item else None for item in equipped),
            (id(weapon), tuple(summon_types)) if summon_types else None,   # tuple: a reroll changes it
        )
        if signature == self.pet_signature:
            return
        self.pet_signature = signature

        existing = {id(p.source_item): p for p in self.pets if p.source_item is not None}

        new_pets = []

        for item in equipped:
            if item is None:
                continue
            if id(item) in existing:
                new_pets.append(existing[id(item)])
            else:
                new_pet = Pet(item.pet_type, self.x, self.y)
                new_pet.source_item = item
                new_pets.append(new_pet)

        summon_existing = {id(p.summon_key): p for p in self.pets if getattr(p, "summon_key", None) is not None}
        for i, pet_type in enumerate(summon_types):
            key = (weapon, i, pet_type)
            found = None
            for p in self.pets:
                if getattr(p, "summon_key", None) == key:
                    found = p
                    break
            if found is not None:
                new_pets.append(found)
            else:
                new_pet = Pet(pet_type, self.x, self.y)
                new_pet.source_item = None
                new_pet.summon_key = key
                new_pets.append(new_pet)

        self.pets = new_pets
    
    def apply_modifier(self, mod):
        stat = mod.get("stat")
        if stat not in stat_defs:
            return

        amount = mod.get("amount", 0)
        mod_type = mod.get("type")

        if mod_type == "flat":
            self.added_flat[stat] += amount
        elif mod_type == "increased":
            self.increased[stat] += amount / 100
        elif mod_type == "more":
            self.more_multipliers[stat] += amount / 100
    
    def begin_action_lock(self, duration):
        self.action_lock_timer = max(self.action_lock_timer, duration)
        self.move_target = None

    def is_action_busy(self, group):
        if group is None:
            return False
        return self.action_timers.get(group, 0) > 0

    def begin_action(self, group, duration):
        if group is None:
            return
        self.action_timers[group] = max(self.action_timers.get(group, 0), duration)

    def move(self, dt):
        if self.dash_timer > 0:
            self.dash_timer -= dt

        if self.action_lock_timer > 0:
            self.action_lock_timer -= dt

        if self.dash_time_remaining > 0:
            self.move_target = None
            self.try_move(
                self.dash_direction.x * self.movement_speed * self.dash_speed_multiplier * dt,
                self.dash_direction.y * self.movement_speed * self.dash_speed_multiplier * dt
            )
            self.dash_time_remaining -= dt
            return

        if self.action_lock_timer > 0:
            self.move_target = None
            return

        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            direction.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            direction.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            direction.x -= 1
            self.facing = 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            direction.x += 1
            self.facing = -1

        if direction.length() > 0:
            self.move_target = None
            direction = direction.normalize()
            self.try_move(direction.x * self.movement_speed * dt, direction.y * self.movement_speed * dt)
        else:
            self.move_towards_target(dt)
    
    def try_move(self, dx, dy):
        player_radius = 20

        new_x = max(0, min(self.x + dx, world.width))
        player_rect_x = pygame.Rect(new_x - player_radius, self.y - player_radius, player_radius * 2, player_radius * 2)
        if not any(o.blocks_movement and world_rect_at(o).colliderect(player_rect_x) for o in world.world_objects):
            self.x = new_x

        new_y = max(0, min(self.y + dy, world.height))
        player_rect_y = pygame.Rect(self.x - player_radius, new_y - player_radius, player_radius * 2, player_radius * 2)
        if not any(o.blocks_movement and world_rect_at(o).colliderect(player_rect_y) for o in world.world_objects):
            self.y = new_y

    def move_towards_target(self, dt):
        order = self.move_target
        if order is None:
            return
        if not order.is_valid():
            self.move_target = None
            return

        dx = order.target.x - self.x
        dy = order.target.y - self.y
        distance = (dx * dx + dy * dy) ** 0.5

        if distance <= order.radius:
            self.move_target = None
            order.on_arrive()
            return

        move_dir = pygame.Vector2(dx, dy).normalize()
        self.facing = 1 if move_dir.x < 0 else -1
        self.try_move(move_dir.x * self.movement_speed * dt, move_dir.y * self.movement_speed * dt)

    def draw_player(self, camera):
        sprite = scaled_sprites[self.sprite_name]

        if self.facing == -1:
            sprite = pygame.transform.flip(sprite, True, False)

        pos = camera.apply_camera(self.x, self.y)
        rect = sprite.get_rect(center=pos)
        rect.center = pos

    #shadow
        shadow_surface = pygame.Surface((rect.width, rect.height // 2), pygame.SRCALPHA)
        shadow_width = int(rect.width * 0.8)
        shadow_height = int(rect.height * 0.25)
        shadow_x = shadow_surface.get_width() // 2
        shadow_y = shadow_surface.get_height() // 2
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 50), (shadow_x - shadow_width // 2, shadow_y - shadow_height // 2, shadow_width, shadow_height))
        shadow_rect = shadow_surface.get_rect(center=(rect.centerx, rect.bottom + 2))

        app.screen.blit(shadow_surface, shadow_rect)

        app.screen.blit(sprite, rect)

    def update_abilities(self, dt):
        for ability in self.abilities.values():
            if ability:
                ability.active_gem_update(dt)

        if self.action_timers:
            for group in list(self.action_timers):
                self.action_timers[group] -= dt
                if self.action_timers[group] <= 0:
                    del self.action_timers[group]
    
    def equipped_weapon_class(self):
        weapon = equipment.main_slots.get("weapon")
        return getattr(weapon, "weapon_class", None) if weapon else None

    def use_ability(self, slot, target_pos, camera):
        ability = self.abilities.get(slot)
        if not ability:
            return False

        if ability.timer > 0:
            return False
        if self.is_action_busy(ability.action_group):
            return False

        weapon_class = self.equipped_weapon_class()

        required = getattr(ability, "weapon_classes", None)
        if required and weapon_class not in required:
            return False

        required_tags = getattr(ability, "weapon_tags", None)
        if required_tags and not (weapon_class_tags(weapon_class) & set(required_tags)):
            return False

        self.move_target = None
        ability.try_cast(self, target_pos, camera)
        return True
    
    def get_sort_y(self):
        return self.y
    
player = Player("witch_front_sprite", 1500, 1500)
#region Leaps and jumps (movement)

class LeapMotion:
    def __init__(self, start_x, start_y, target_x, target_y, height, time_per_unit,
                 max_distance=None, min_distance=0, scatter=0):
        if scatter > 0:
            target_x += random.uniform(-scatter, scatter)
            target_y += random.uniform(-scatter, scatter)

        dx = target_x - start_x
        dy = target_y - start_y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < min_distance:
            if dist > 0:
                scale = min_distance / dist
                target_x = start_x + dx * scale
                target_y = start_y + dy * scale
            else:
                angle = random.uniform(0, 360)
                offset = pygame.Vector2(min_distance, 0).rotate(angle)
                target_x = start_x + offset.x
                target_y = start_y + offset.y
            dx = target_x - start_x
            dy = target_y - start_y
            dist = (dx * dx + dy * dy) ** 0.5

        if max_distance is not None and dist > max_distance and dist > 0:
            scale = max_distance / dist
            target_x = start_x + dx * scale
            target_y = start_y + dy * scale
            dist = max_distance

        self.start_x = start_x
        self.start_y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.height = height
        self.duration = max(0.01, dist * time_per_unit)
        self.elapsed = 0.0
        self.done = False
        self.height_offset = 0.0  

    def update(self, dt):
        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)
        x = self.start_x + (self.target_x - self.start_x) * t
        y = self.start_y + (self.target_y - self.start_y) * t
        # parabola: 0 at t=0 and t=1, peaks at `height` when t=0.5
        self.height_offset = self.height * 4 * t * (1 - t)
        if t >= 1.0:
            self.done = True
        return x, y

def begin_leap(entity, target_x, target_y, height, time_per_unit, max_distance=None, min_distance=0, scatter=0):
    entity.leap = LeapMotion(entity.x, entity.y, target_x, target_y, height, time_per_unit, max_distance, min_distance, scatter)

def update_leap(entity, dt):
    leap = getattr(entity, "leap", None)
    if leap is None:
        return False
    entity.x, entity.y = leap.update(dt)
    if leap.done:
        entity.leap = None
    return True

def leap_height_offset(entity):
    leap = getattr(entity, "leap", None)
    return leap.height_offset if leap else 0.0

