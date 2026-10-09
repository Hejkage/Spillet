"""TREE VIEW - zoom and drag for every tree screen (the skill tree, gem trees...).

A tree panel owns one TreeView and asks it where things go:
    view.fit(positions)          zoom so the whole tree fits, centred
    view.to_screen(x, y)         tree position -> screen position
    view.zoom                    the current zoom (multiply sizes by it)
    view.sprite(name)            a sprite at the current zoom (pixel-perfect)

Input, all forwarded by the panel:
    view.press(pos)              left mouse down
    view.release(pos) -> bool    left mouse up. True = it was a CLICK, not a drag
    view.scroll(steps, pos)      mouse wheel: zoom towards the mouse
    view.update()                every frame: dragging and arrow keys / WASD

Zoom only uses the fixed steps below, so pixel art never scales unevenly.
"""
import pygame
from core.state import app

zoom_steps = [0.25, 0.5, 1, 2, 3, 4]
fit_max_zoom = 2            # a small tree is never fitted bigger than this
fit_margin = 90             # space around the tree when it is fitted (screen pixels)
drag_threshold = 6          # the mouse must move this far before a press becomes a drag
key_pan_speed = 900         # screen pixels per second with the arrow keys / WASD
pan_keys = {
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
    pygame.K_UP: (0, -1),   pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),  pygame.K_s: (0, 1),
}

class TreeView:
    def __init__(self):
        self.zoom_index = zoom_steps.index(1)
        self.center = pygame.Vector2(0, 0)          # the tree position in the middle of the screen
        self.bounds = pygame.Rect(0, 0, 1, 1)       # the area the nodes cover (tree pixels)
        self.fitted = False
        self.press_pos = None
        self.last_mouse = None
        self.dragging = False
        self.last_tick = None
        self._sprite_cache = {}

    @property
    def zoom(self):
        return zoom_steps[self.zoom_index]

    # --- where things go ------------------------------------------------
    def to_screen(self, x, y):
        z = self.zoom
        return (int(app.screen_width / 2 + (x - self.center.x) * z),
                int(app.screen_height / 2 + (y - self.center.y) * z))

    def to_tree(self, sx, sy):
        z = self.zoom
        return pygame.Vector2(self.center.x + (sx - app.screen_width / 2) / z,
                              self.center.y + (sy - app.screen_height / 2) / z)

    def fit(self, positions):
        """Zoom out until every position fits on screen, centred on the tree."""
        positions = list(positions) or [(0, 0)]
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        self.bounds = pygame.Rect(min(xs), min(ys), max(1, max(xs) - min(xs)), max(1, max(ys) - min(ys)))
        self.center = pygame.Vector2(self.bounds.center)
        room_w = max(1, app.screen_width - fit_margin * 2)
        room_h = max(1, app.screen_height - fit_margin * 2)
        self.zoom_index = 0
        for i, z in enumerate(zoom_steps):
            if z <= fit_max_zoom and self.bounds.w * z <= room_w and self.bounds.h * z <= room_h:
                self.zoom_index = i
        self.fitted = True

    def sprite(self, name):
        """The sprite at the current zoom, or None if it doesn't exist."""
        from core.assets import sprites
        base = sprites.get(name)
        if base is None:
            return None
        key = (name, self.zoom)
        if key not in self._sprite_cache:
            w, h = base.get_size()
            self._sprite_cache[key] = pygame.transform.scale(
                base, (max(1, int(w * self.zoom)), max(1, int(h * self.zoom))))
        return self._sprite_cache[key]

    # --- input ------------------------------------------------------------
    def scroll(self, steps, mouse_pos):
        """Zoom one step per wheel notch, keeping the point under the mouse still."""
        new_index = max(0, min(len(zoom_steps) - 1, self.zoom_index + steps))
        if new_index == self.zoom_index:
            return
        anchor = self.to_tree(*mouse_pos)
        self.zoom_index = new_index
        z = self.zoom
        self.center = pygame.Vector2(anchor.x - (mouse_pos[0] - app.screen_width / 2) / z,
                                     anchor.y - (mouse_pos[1] - app.screen_height / 2) / z)
        self._clamp()

    def press(self, pos):
        self.press_pos = pos
        self.last_mouse = pos
        self.dragging = False

    def release(self, pos):
        """True if this was a click (the mouse didn't drag)."""
        was_click = self.press_pos is not None and not self.dragging
        self.press_pos = None
        self.dragging = False
        return was_click

    def update(self):
        now = pygame.time.get_ticks()
        dt = 0 if self.last_tick is None else min(0.1, (now - self.last_tick) / 1000)
        self.last_tick = now

        if self.press_pos is not None:
            if not pygame.mouse.get_pressed()[0]:
                self.press_pos = None                       # released somewhere we didn't hear about
                self.dragging = False
            else:
                mouse = pygame.mouse.get_pos()
                if not self.dragging and pygame.Vector2(mouse).distance_to(self.press_pos) > drag_threshold:
                    self.dragging = True
                if self.dragging:
                    self.center -= pygame.Vector2(mouse[0] - self.last_mouse[0], mouse[1] - self.last_mouse[1]) / self.zoom
                self.last_mouse = mouse

        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        for key, (dx, dy) in pan_keys.items():
            if keys[key]:
                move += (dx, dy)
        if move.length_squared() > 0:
            self.center += move.normalize() * key_pan_speed * dt / self.zoom
        self._clamp()

    def _clamp(self):
        """Never lose the tree: the middle of the screen stays over the tree area."""
        self.center.x = max(self.bounds.left, min(self.bounds.right, self.center.x))
        self.center.y = max(self.bounds.top, min(self.bounds.bottom, self.center.y))
