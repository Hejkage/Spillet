import pygame
import math
from core.state import app
from systems.weapons import get_swing_sprite, get_weapon_geometry, melee_reach, melee_weapon_sprite, player_body_radius
from systems.supports import apply_support_gems

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Melee attacks ###########################################################################

melee_swings = []

def angle_difference(a, b):
    return (a - b + 180) % 360 - 180

class MeleeSwing:
    def __init__(self, owner, aim_angle, arc, radius, duration, damage, effects=None, hit_stats=None, sprite_name=None, sprite_angle_offset=0.0, hand_reach=None, hand_offset_y=None, sweep_dir=1, max_targets=0, from_player=True):

        self.owner = owner
        self.arc = arc
        self.radius = radius
        self.duration = max(0.01, duration)
        self.elapsed = 0.0
        self.damage = damage
        self.hit_stats = hit_stats or {}
        self.effects = list(effects) if effects else []
        self.from_player = from_player
        self.max_targets = max_targets
        self.hit_enemies = set()
        self.alive = True

        self.sweep_dir = sweep_dir
        self.start_angle = aim_angle - (arc / 2) * sweep_dir
        self.current_angle = self.start_angle

        self.sprite_angle_offset = sprite_angle_offset

        geom = get_weapon_geometry(sprite_name) if sprite_name else None
        if geom and geom["length"] > 0:
            base_reach = player_body_radius + geom["reach"]
            self.visual_scale = self.radius / base_reach if base_reach > 0 else 1.0

            flip_v = math.cos(math.radians(aim_angle)) < 0
            self.sprite = get_swing_sprite(sprite_name, self.visual_scale, flip_v)

            unscaled_hand = player_body_radius if hand_reach is None else hand_reach
            unscaled_center = unscaled_hand + (geom["length"] / 2 - geom["grip"])

            self.hand_reach = unscaled_hand * self.visual_scale
            self.hand_offset_y = geom["hand_offset_y"] if hand_offset_y is None else hand_offset_y
            self.center_distance = unscaled_center * self.visual_scale
        else:
            self.visual_scale = 1.0
            self.sprite = None
            self.hand_reach = 0
            self.hand_offset_y = 0
            self.center_distance = 0
    
    def origin(self):
        return self.owner.x, self.owner.y + self.hand_offset_y

    def sprite_position(self):
        ox, oy = self.origin()
        offset = pygame.Vector2(self.center_distance, 0).rotate(self.current_angle)
        return ox + offset.x, oy + offset.y

    def update(self, dt):
        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)
        self.current_angle = self.start_angle + self.arc * t * self.sweep_dir

        self.apply_hits(t)

        if self.elapsed >= self.duration:
            self.alive = False

    def apply_hits(self, t):
        from systems.enemies import apply_player_hit, enemy_grid
        if not self.from_player:
            return
        if self.max_targets and len(self.hit_enemies) >= self.max_targets:
            return

        swept = self.arc * t
        reach = self.radius
        ox, oy = self.origin()

        for enemy in enemy_grid.query_radius(ox, oy, reach):
            if not enemy.alive or enemy in self.hit_enemies:
                continue

            body = max(enemy.rect.width, enemy.rect.height) * 0.5

            dx = enemy.x - ox
            dy = enemy.y - oy
            dist_sq = dx * dx + dy * dy
            if dist_sq > (reach + body) * (reach + body):
                continue

            dist = dist_sq ** 0.5
            enemy_angle = math.degrees(math.atan2(dy, dx))
            slack = math.degrees(math.asin(min(1.0, body / dist))) if dist > 0 else 180

            progress = angle_difference(enemy_angle, self.start_angle) * self.sweep_dir
            if progress < -slack or progress > swept + slack:
                continue

            self.hit_enemies.add(enemy)
            apply_player_hit(enemy, self.damage, self.effects, self.hit_stats)

            if self.max_targets and len(self.hit_enemies) >= self.max_targets:
                return

    def draw(self, camera):
        if self.sprite is None:
            return
        sx, sy = self.sprite_position()
        rotated = pygame.transform.rotate(self.sprite, -(self.current_angle + self.sprite_angle_offset))
        app.screen.blit(rotated, rotated.get_rect(center=camera.apply_camera(sx, sy)))
    
    def draw_debug(self, camera):
        ox, oy = self.origin()
        origin = camera.apply_camera(ox, oy)

        segments = max(8, int(self.arc / 6))
        t = min(1.0, self.elapsed / self.duration)

        # full cone the swing will cover
        full = [origin]
        for i in range(segments + 1):
            a = self.start_angle + (self.arc * i / segments) * self.sweep_dir
            offset = pygame.Vector2(self.radius, 0).rotate(a)
            full.append((origin[0] + offset.x, origin[1] + offset.y))
        pygame.draw.lines(app.screen, (90, 90, 200), True, full, 1)

        # portion already swept (this is what has actually dealt damage)
        swept_pts = [origin]
        swept_segs = max(1, int(segments * t))
        for i in range(swept_segs + 1):
            a = self.start_angle + (self.arc * t * i / swept_segs) * self.sweep_dir
            offset = pygame.Vector2(self.radius, 0).rotate(a)
            swept_pts.append((origin[0] + offset.x, origin[1] + offset.y))
        pygame.draw.lines(app.screen, (255, 220, 80), True, swept_pts, 2)

        # blade line at the current angle
        tip = pygame.Vector2(self.radius, 0).rotate(self.current_angle)
        pygame.draw.line(app.screen, (255, 60, 60),
                         origin, (origin[0] + tip.x, origin[1] + tip.y), 2)

        # where the sprite is anchored
        # grip (hand) and blade tip along the current angle
        hand = pygame.Vector2(self.hand_reach, 0).rotate(self.current_angle)
        pygame.draw.circle(app.screen, (60, 255, 120), camera.apply_camera(ox + hand.x, oy + hand.y), 4)
        pygame.draw.circle(app.screen, (60, 255, 120), camera.apply_camera(ox + tip.x, oy + tip.y), 4)

        # enemies this swing has already hit
        for enemy in self.hit_enemies:
            pygame.draw.rect(app.screen, (255, 60, 60), enemy.rect, 2)

    def get_sort_y(self):
        return self.owner.y

def update_melee_swings(dt):
    if not melee_swings:
        return
    for swing in melee_swings:
        swing.update(dt)
    melee_swings[:] = [s for s in melee_swings if s.alive]

def draw_melee_swings(camera):
    for swing in melee_swings:
        swing.draw(camera)
        if app.debug_hitboxes:
            swing.draw_debug(camera)

def cast_melee_attack(player, target_pos, camera, damage, aoe, speed, sprite_name, support_gems, extra=None, facing_flip=1):
    extra = extra or {}

    player_screen_pos = pygame.Vector2(camera.apply_camera(player.x, player.y))
    direction = pygame.Vector2(target_pos) - player_screen_pos
    if direction.length_squared() == 0:
        direction = pygame.Vector2(1, 0)

    aim_angle = math.degrees(math.atan2(direction.y, direction.x))

    if direction.x > 0:
        player.facing = -1 * facing_flip
    elif direction.x < 0:
        player.facing = 1 * facing_flip

    data = apply_support_gems(direction, speed, damage, aoe, sprite_name, support_gems, extra=extra)[0]

    swing_sprite = sprite_name
    if extra.get("use_weapon_sprite", True):
        swing_sprite = melee_weapon_sprite(sprite_name)

    aoe_range = data["aoe"] if extra.get("aoe_scales_range", False) else 1.0

    radius = melee_reach(player, swing_sprite, range_mult=extra.get("range_mult", 1.0), aoe=aoe_range)

    arc = extra.get("arc", 110)
    attack_time = extra.get("_interval", 0.25)
    duration = attack_time * extra.get("swing_time", 0.8)

    sweep_dir = 1 if direction.x >= 0 else -1

    effects = []
    if extra.get("dot_duration", 0) > 0:
        effects.append({"name": "dot", "duration": extra["dot_duration"], "dps": extra.get("dot_damage", 0)})

    melee_swings.append(MeleeSwing(
        player, aim_angle, arc, radius, duration, data["damage"],
        hit_stats=data,
        effects=effects,
        sprite_name=swing_sprite,
        sprite_angle_offset=extra.get("sprite_angle_offset", 0.0),
        hand_reach=extra.get("hand_reach"),
        hand_offset_y=extra.get("hand_offset_y"),
        sweep_dir=sweep_dir,
        max_targets=extra.get("max_targets", 0),
    ))
