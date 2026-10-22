import pygame
import random
from core.state import app, world
from core.assets import scaled_sprites
from systems.weapons import weapon_class_tags
from systems.supports import support_gem_types, support_fits
from systems.items import active_gem_slots, equipment, pet_equip_slots, stat_defs, immunity_stats
from systems.damage import fold_damage_stats
from systems.abilities import active_gem_templates, basic_attacks_by_weapon, build_active_gem, ability_tags, ability_blocked
from systems.world_objects import world_rect_at, nearest_free_point, move_with_collision, feet_y
from systems.pets import Pet
from systems.rarity import rarity_common
from core.screen import camera
from systems.facing import face_direction, facing_sprite_name, facing_surface
from systems.skilltree import allocated_points, allocated_sources
from systems.mods import hit_key
from systems.bonuses import collect_bonuses
from systems.status import StatusHolder, draw_statuses
import systems.ailments        # registers the burn / poison stats BEFORE the player is created
import systems.leech           # registers spell leech BEFORE the player is created
from systems.resources import clamp_resources, fill_resources, regen_resources, can_pay, pay
from systems.attributes import attribute_values, attribute_bonuses, attribute_lines

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Player
class MoveOrder:
    def __init__(self, target, radius, on_arrive, is_valid=None):
        self.target = target                   
        self.radius = radius                    
        self.on_arrive = on_arrive            
        self.is_valid = is_valid or (lambda: True)  

def equipment_items():
    """Every equipped gear item and gem, working or not."""
    return [i for i in list(equipment.main_slots.values()) + list(equipment.extra_slots.values()) if i]

def weapon_allows(ability, weapon_class):
    """Does this weapon class let you use this ability? (its weapon_classes / weapon_tags)"""
    required = getattr(ability, "weapon_classes", None)
    if required and weapon_class not in required:
        return False
    required_tags = getattr(ability, "weapon_tags", None)
    if required_tags and not (weapon_class_tags(weapon_class) & set(required_tags)):
        return False
    return True

summon_rarity = rarity_common     # rarity of pets from "summons" on items and tree nodes

class _Spot:
    def __init__(self, x, y):
        self.x, self.y = x, y

mouse_move_stop_radius = 6        # how close to the cursor counts as "there"

def mouse_move_order():
    """Walk to the spot under the mouse (mouse movement mode)."""
    mx, my = pygame.mouse.get_pos()
    return MoveOrder(_Spot(mx + camera.x, my + camera.y), mouse_move_stop_radius, lambda: None)

class Player(StatusHolder):
    def __init__(self, sprite_name, player_x, player_y):
        self.sprite_name = sprite_name
        self.back_sprite_name = "witch_back_sprite"
        self.x = player_x
        self.y = player_y
        self.facing = 1
        self.facing_y = 1 
        self.coins = 0
        self.xp = 0
        self.level = 1
        self.xp_to_next_level = 1000
        self.move_target = None
        self.statuses = {}
        self.abilities = {"primary": None}
        for slot in active_gem_slots:
            self.abilities[slot] = None
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
            face_direction(self, direction.x, direction.y)
    
    def use_dash(self):
        self.try_dash()

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = int(self.xp_to_next_level * 1.25 * (1 + self.level / 100))
            from systems.popups import spawn_floating_text
            spawn_floating_text("Level Up! +1 Skill Point", self.x, self.y - 40, color=(255, 230, 120))

    def take_damage(self, amount, flash=True):
        if self.current_health <= 0:
            return
        if flash and amount > 0:
            from systems.hitflash import flash as hit_flash
            hit_flash(self)
        self.current_health -= amount
        if self.current_health <= 0:
            self.current_health = 0
            self.die()
    
    def heal(self, amount):
        self.current_health = min(self.max_health, self.current_health + amount)

    def defence_stat(self, stat):
        """Used by resolve_damage(). Enemies have the same method.
        "fire_resistance" already includes "elemental_resistance"."""
        return self.damage_totals.get(stat, 0)

    def stat_value(self, stat):
        """What the stats panel shows for a stat."""
        if stat in self.damage_totals:
            return self.damage_totals[stat]
        return getattr(self, stat, 0)

    def die(self):
        from systems.areas import areas, switch_area
        self.current_health = self.max_health
        fill_resources(self)
        switch_area(areas["home"])
    
    def update_health(self, dt):
        if self.health_regen > 0 and self.current_health > 0:
            self.heal(self.health_regen * dt)
        regen_resources(self, dt)                            # mana (and later other resources)
    
    def resolve_stat(self, key, hit_stats=None):
        s = hit_stats or {}
        flat = self.base_stats[key] + self.added_flat[key] + s.get(hit_key(key), 0)   # + what this hit carries
        inc = 1 + self.increased[key] + s.get(key + "_increase", 0) / 100
        return flat * inc

    def crit_stats(self, hit_stats=None):
        s = hit_stats or {}
        hit_type = s.get("hit_type", "attack")
        chance_stat = "spell_crit_chance" if hit_type == "spell" else "attack_crit_chance"

        flat = (self.base_stats[chance_stat] + self.added_flat[chance_stat]
                + self.base_stats["crit_chance"] + self.added_flat["crit_chance"]
                + s.get(chance_stat, 0) + s.get("crit_chance", 0))

        inc = (1 + self.increased[chance_stat] + self.increased["crit_chance"]
               + s.get(chance_stat + "_increase", 0) / 100
               + s.get("crit_chance_increase", 0) / 100)

        return (flat * inc, self.resolve_stat("crit_damage", hit_stats))

    def effect_crit_stats(self):
        """Crit for effects (explosions...). Their base crit chance is 0%, so only
        ADDED crit chance counts, then increased crit chance like everything else:
        250% increased on 0 is still 0. Attack / spell crit chance never count."""
        chance = self.added_flat["crit_chance"] * (1 + self.increased["crit_chance"])
        return (chance, self.resolve_stat("crit_damage"))

    def effect_more_damage(self):
        """Every "more_damage" you have (items, passive tree) as one multiplier: 1.2 = 20% more."""
        from systems.mods import combine_values
        values = [value for name, value in getattr(self, "outside_mods", ()) if name == "more_damage"]
        return 1 + combine_values("more_damage", values) / 100

    def has_grant(self, name):
        """True if the tree (or anything else filling grants) allows this."""
        return bool(getattr(self, "grants", {}).get(name))

    def grant_value(self, name, default=0):
        """How much of a numeric grant the player has, e.g. extra ring slots."""
        return getattr(self, "grants", {}).get(name, default)

    def effects_for(self, event):
        """The effect data the tree attached to this event, e.g. "on_kill"."""
        return getattr(self, "event_effects", {}).get(event, ())

    def bonus_sources(self):
        """[(key, item_or_node), ...] - everything that gives the player bonuses:
        working items, allocated tree nodes, and what your attributes give.
        Disabled items (red slot, e.g. an offhand after losing Titan Grip) give nothing."""
        return ([(id(item), item) for _, item in equipment.working_items()] + allocated_sources()
                + [("attributes", attribute_bonuses(getattr(self, "attributes", {})))])

    def recalculate_stats(self, force=False):
        equip_signature = tuple(id(i) if i else None for i in list(equipment.main_slots.values()) + list(equipment.extra_slots.values()))
        from systems.pets import pet_signature, update_pet_stats
        signature = (equip_signature, tuple(sorted(allocated_points.items())), pet_signature(self.pets))   # a respec changes the points
        if not force and signature == getattr(self, "_stat_signature", None):
            return
        self._stat_signature = signature
        for key, d in stat_defs.items():                    # a stat registered from content/ after the player was made
            if key not in self.base_stats:
                self.base_stats[key] = d["base"]
                self.added_flat[key] = 0
                self.increased[key] = 0
        for stat in self.base_stats:
            self.added_flat[stat] = 0
            self.increased[stat] = 0
        # Which items WORK depends on grants (a third ring, Titan Grip) and on
        # attributes (requirements) - and those come from the items that work.
        # So: start with everything worn, then repeat until nothing changes.
        working = equipment_items()
        for _ in range(5):
            sources = [(id(i), i) for i in working] + allocated_sources()
            totals = collect_bonuses(sources)
            self.attribute_lines = attribute_lines(sources)              # (source, line) - for "what if I equip this"
            self.attributes = attribute_values([line for _, line in self.attribute_lines])   # an item's own attributes count
            from_attributes = attribute_bonuses(self.attributes)
            self.grants = dict(totals["grants"])
            for name, value in from_attributes.get("grants", {}).items():
                self.grants[name] = self.grants.get(name, 0) + (1 if value is True else value)
            still_working = [item for _, item in equipment.working_items()]
            if [id(i) for i in still_working] == [id(i) for i in working]:
                break
            working = still_working
        # everything working items, tree nodes and attributes give (systems/bonuses.py)
        bonuses = collect_bonuses(self.bonus_sources())
        for mod in bonuses["stats"]:
            self.apply_modifier(mod)
        # pets read your "pet_..." stats from above, then their auras land on you
        for mod in update_pet_stats(self):
            self.apply_modifier(mod)
        for stat in self.base_stats:
            setattr(self, stat, self.resolve_stat(stat))
        # immunities: "poison_immunity" 100 or more -> poison is in self.immune. Less is a chance.
        from systems.items import immunity_full
        self.immune = {status for stat, status in immunity_stats.items() if getattr(self, stat, 0) >= immunity_full}
        for status in self.immune:
            self.statuses.pop(status, None)          # becoming immune removes it right away
        self.damage_totals = fold_damage_stats(lambda s: getattr(self, s, 0))
        if hasattr(self, "current_health"):
            self.current_health = min(self.current_health, self.max_health)
        clamp_resources(self)                                # mana can't stay above a lower max

        # what items and the tree give besides plain stats
        self.outside_mods = bonuses["mods"]
        self.grants = bonuses["grants"]
        self.event_effects = bonuses["effects"]

    def rebuild_basic_attack(self):
        weapon_class = self.equipped_weapon_class()
        if weapon_class == self.basic_attack_signature:
            return
        self.basic_attack_signature = weapon_class

        self.abilities["primary"] = basic_attacks_by_weapon.get(
            weapon_class, basic_attacks_by_weapon[None]
        )

    def rebuild_gem_ability(self):
        from systems.gemtree import tree_supports, tree_mods, tree_effects
        outside_mods = list(getattr(self, "outside_mods", ()))
        signature = []
        for slot in active_gem_slots:
            item = equipment.extra_slots.get(slot)
            socket_ids = tuple(sorted((k, id(v)) for k, v in item.tree.sockets.items())) if item else ()
            tree_points = tuple(sorted(item.tree.saved.items())) if item else ()    # a respec of THIS gem
            signature.append((id(item) if item else None, socket_ids, tree_points, tuple(outside_mods), equipment.is_disabled(slot)))
        signature = tuple(signature)
        if signature == self.gem_signature:      # <-- without this the gem is rebuilt every frame
            return
        self.gem_signature = signature           # <-- and without this too

        for slot in active_gem_slots:
            active_item = equipment.extra_slots.get(slot)
            if active_item is None or equipment.is_disabled(slot):   # red gem (requirement not met): no ability
                self.abilities[slot] = None
                continue
            supports = list(tree_supports(active_item))
            built_in = getattr(active_item, "built_in_support", None)
            if built_in is not None:
                supports = [built_in] + supports
            t = active_gem_templates[active_item.template_key]
            tags, blocked = ability_tags(t), ability_blocked(t)
            supports = [s for s in supports if support_fits(s.gem_type, tags, blocked)]
            self.abilities[slot] = build_active_gem(
                t, supports,
                gem_stats=getattr(active_item, "gem_stats", None),
                outside_mods=outside_mods,
                tree_mods=tree_mods(active_item),            # only THIS gem's tree
                tree_effects=tree_effects(active_item))

    def rebuild_pets(self):
        equipped = [None if equipment.is_disabled(s) else equipment.pet_slots[s] for s in pet_equip_slots]

        # pets from "summons" on items and tree nodes: [(source, pet_type, number), ...]
        summons = collect_bonuses(self.bonus_sources())["summons"]

        signature = (
            tuple(id(item) if item else None for item in equipped),
            tuple(summons),
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
                new_pet = Pet(item.pet_type, self.x, self.y, rarity=item.rarity, source_item=item)
                new_pets.append(new_pet)

        summoned = {p.summon_key: p for p in self.pets if getattr(p, "summon_key", None) is not None}
        for key in summons:
            pet = summoned.get(key)
            if pet is None:
                source_key, pet_type, number = key
                pet = Pet(pet_type, self.x, self.y, rarity=summon_rarity)
                pet.summon_key = key
            new_pets.append(pet)

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

        from core.keybinds import action_held, movement_mode
        if movement_mode() == "mouse":
            if app.mouse_move_active:
                if action_held("move_to_mouse"):
                    self.move_target = mouse_move_order()          # follow the cursor while held
                else:
                    app.mouse_move_active = False                  # let go: finish walking to the last spot
            self.move_towards_target(dt)
            return

        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)

        if action_held("move_up") or keys[pygame.K_UP]:          # the arrow keys always work too
            direction.y -= 1
        if action_held("move_down") or keys[pygame.K_DOWN]:
            direction.y += 1
        if action_held("move_left") or keys[pygame.K_LEFT]:
            direction.x -= 1
        if action_held("move_right") or keys[pygame.K_RIGHT]:
            direction.x += 1

        if direction.length() > 0:
            face_direction(self, direction.x, direction.y)
            self.move_target = None
            direction = direction.normalize()
            self.try_move(direction.x * self.movement_speed * dt, direction.y * self.movement_speed * dt)
        else:
            self.move_towards_target(dt)
    
    def try_move(self, dx, dy):
        move_with_collision(self, dx, dy, 20)
        self.x = max(0, min(self.x, world.width))
        self.y = max(0, min(self.y, world.height))

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
        face_direction(self, move_dir.x, move_dir.y)
        self.try_move(move_dir.x * self.movement_speed * dt, move_dir.y * self.movement_speed * dt)

    def draw_player(self, camera):
        sprite = facing_surface(self, scaled_sprites[facing_sprite_name(self)])

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
        draw_statuses(self, rect.centerx, rect.top - 4)

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
        if weapon is None or equipment.is_disabled("weapon"):    # a red weapon is like no weapon
            return None
        return getattr(weapon, "weapon_class", None)

    def equipped_weapons(self):
        """[main weapon, offhand weapon] - only the ones that are there.
        A shield in the offhand is not a weapon, so it is left out."""
        found = []
        for slot in ("weapon", "offhand"):
            item = equipment.main_slots.get(slot)
            if item is not None and getattr(item, "slot_type", None) == "weapon" and not equipment.is_disabled(slot):
                found.append(item)
        return found

    def has_usable_ability(self, slot):
        """True if this slot holds an ability one of your weapons allows - even
        while it is on cooldown. With a wand + gun you can use wand AND gun
        abilities (the basic attack still comes from the main weapon only)."""
        ability = self.abilities.get(slot)
        if not ability:
            return False
        classes = [w.weapon_class for w in self.equipped_weapons()] or [None]    # None = no weapon
        return any(weapon_allows(ability, weapon_class) for weapon_class in classes)

    def use_ability(self, slot, target_pos, camera):
        if not self.has_usable_ability(slot):
            return False
        ability = self.abilities[slot]

        if ability.timer > 0:
            return False
        if self.is_action_busy(ability.action_group):
            return False
        cost = getattr(ability, "cost", None)
        if not can_pay(self, cost):                          # not enough mana
            return False

        self.move_target = None
        ability.try_cast(self, target_pos, camera)
        pay(self, cost)
        return True
    
    def get_sort_y(self):
        return feet_y(self.y, scaled_sprites[facing_sprite_name(self)])
    
player = Player("witch_front_sprite", 1500, 1500)
#region Leaps and jumps (movement)

class LeapMotion:
    def __init__(self, start_x, start_y, target_x, target_y, height, time_per_unit, max_distance=None, min_distance=0, scatter=0, radius=20):
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

        target_x, target_y = nearest_free_point(start_x, start_y, target_x, target_y, radius)
        dist = ((target_x - start_x) ** 2 + (target_y - start_y) ** 2) ** 0.5

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
    radius = getattr(entity, "collision_radius", 20)
    entity.leap = LeapMotion(entity.x, entity.y, target_x, target_y, height, time_per_unit, max_distance, min_distance, scatter, radius)

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

