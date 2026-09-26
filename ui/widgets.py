import pygame
from core.state import app
from core.screen import get_font
from core.assets import scaled_sprites, get_ui_scaled
from systems.ground import assign_label_slots, loot_filter_levels


# region Buttons

class Button:
    def __init__(self, sprite_name, text, position, anchor="center", action=None):
        self.sprite_name = sprite_name
        self.text = text
        self.position = position
        self.anchor = anchor
        self.action = action
        self.rect = None
    
    def get_pixel_pos(self):
        return (int(self.position[0] * app.screen_width), int(self.position[1] * app.screen_height))

    def update(self):
        sprite = scaled_sprites[self.sprite_name]
        pos = self.get_pixel_pos()
        self.rect = sprite.get_rect()

        if self.anchor == "center":
            self.rect.center = pos
        elif self.anchor == "top_left":
            self.rect.topleft = pos
        elif self.anchor == "top_right":
            self.rect.topright = pos
        elif self.anchor == "bottom_left":
            self.rect.bottomleft = pos
        elif self.anchor == "bottom_right":
            self.rect.bottomright = pos

    def draw_button(self):
        self.update()
        sprite = scaled_sprites[self.sprite_name]
        app.screen.blit(sprite, self.rect)

        font_scale = min(app.screen_width, app.screen_height)
        font = get_font(int(font_scale * 0.04))

        text = font.render(self.text, False, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        app.screen.blit(text, text_rect)

class Dropdown:
    all_dropdowns = []

    def __init__(self, position, options, anchor="center", on_select=None, get_label=None, header_label=None):
        self.position = position
        self.anchor = anchor
        self.options = options
        self.on_select = on_select
        self.get_label = get_label or (lambda v: str(v))
        self.header_label = header_label
        self.selected_index = 0
        self.open = False
        self.rect = None
        self.option_rects = []
        Dropdown.all_dropdowns.append(self)

    @classmethod
    def close_open(cls):
        closed_one = False
        for d in cls.all_dropdowns:
            if d.open:
                d.open = False
                closed_one = True
        return closed_one
    
    def current_value(self):
        return self.options[self.selected_index]
    
    def get_pixel_pos(self):
        return (int(self.position[0]* app.screen_width), int(self.position[1] * app.screen_height))
    
    def header_rect(self, sprite):
        rect = sprite.get_rect()
        pos = self.get_pixel_pos()
        setattr(rect, self.anchor, pos)
        return rect
    
    def draw(self):
        sprite = scaled_sprites["dropdown_background_sprite"]
        self.rect = self.header_rect(sprite)

        if self.open:
            overlay = pygame.Surface((app.screen_width, app.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            app.screen.blit(overlay, (0, 0))

        app.screen.blit(sprite, self.rect)

        font = get_font(int(min(app.screen_width, app.screen_height) * 0.03))
        header_fn = self.header_label or self.get_label
        lines = header_fn(self.current_value())
        if isinstance(lines, str):
            lines = [lines]
        rendered = [font.render(line, True, (255, 255, 255)) for line in lines]
        total_h = sum(r.get_height() for r in rendered)
        y = self.rect.centery - total_h // 2
        for r in rendered:
            app.screen.blit(r, r.get_rect(centerx=self.rect.centerx, top=y))
            y += r.get_height()

        self.option_rects = []
        if self.open:
            self._draw_option_list(font)

    def _draw_option_list(self, font):
        row_h = int(self.rect.height * 0.8)
        list_rect = pygame.Rect(self.rect.left, self.rect.bottom, self.rect.width, row_h * len(self.options))
        list_sprite = get_ui_scaled("button_sprite", list_rect.width, list_rect.height)
        app.screen.blit(list_sprite, list_rect)

        mouse_pos = pygame.mouse.get_pos()
        for i, value in enumerate(self.options):
            opt_rect = pygame.Rect(list_rect.left, list_rect.top + i * row_h, list_rect.width, row_h)
            self.option_rects.append(opt_rect)

            if i == self.selected_index:
                pygame.draw.rect(app.screen, (90, 130, 90), opt_rect)
            elif opt_rect.collidepoint(mouse_pos):
                pygame.draw.rect(app.screen, (70, 70, 70), opt_rect)

            if i > 0:
                pygame.draw.line(app.screen, (200, 200, 200), opt_rect.topleft, opt_rect.topright, 1)

            opt_text = font.render(self.get_label(value), True, (255, 255, 255))
            app.screen.blit(opt_text, opt_text.get_rect(center=opt_rect.center))
    
    def handle_click(self, pos):
        if self.open:
            for i, opt_rect in enumerate(self.option_rects):
                if opt_rect.collidepoint(pos):
                    self.selected_index = i
                    self.open = False
                    if self.on_select:
                        self.on_select(self.current_value())
                    return True
                
            if self.rect and self.rect.collidepoint(pos):
                self.open = False
                return True
            self.open = False
            return True
        else:
            if self.rect and self.rect.collidepoint(pos):
                self.open = True
                return True
        return False
    
class Checkbox:
    def __init__(self, position, size=28, anchor="center", get_state=None, on_toggle=None):
        self.position = position
        self.size = size
        self.anchor = anchor
        self.get_state = get_state      # returns current bool
        self.on_toggle = on_toggle      # called with the new bool
        self.rect = None

    def get_pixel_pos(self):
        return (int(self.position[0] * app.screen_width), int(self.position[1] * app.screen_height))

    def draw(self):
        scale = app.ui_scale
        s = max(1, int(self.size * scale))
        self.rect = pygame.Rect(0, 0, s, s)
        setattr(self.rect, self.anchor, self.get_pixel_pos())

        pygame.draw.rect(app.screen, (60, 60, 60), self.rect)
        pygame.draw.rect(app.screen, (200, 200, 200), self.rect, 2)

        if self.get_state and self.get_state():
            inner = self.rect.inflate(-int(s * 0.4), -int(s * 0.4))
            pygame.draw.rect(app.screen, (80, 200, 80), inner)

    def handle_click(self, pos):
        if self.rect and self.rect.collidepoint(pos):
            if self.on_toggle:
                self.on_toggle(not self.get_state())
            return True
        return False

buttons = [
    Button("button_sprite", "Fullscreen", (0.2, 0.32), action="toggle_fullscreen"),
    Button("button_sprite", "Quit", (0.2, 0.44), action="quit"),
    Button("button_sprite", "Save and exit", (0.2, 0.56), action="save_exit"),
    Button("button_sprite", "Restart", (0.2, 0.68), action="restart"),
    Button("button_sprite", "Main Menu", (0.2, 0.80), action="menu")
]
for b in buttons:
    b.update()

menu_buttons = [
    Button("button_sprite", "Start Game", (0.5, 0.38), action="play"),
    Button("button_sprite", "Quit", (0.5, 0.50), action="quit"),
    Button("button_sprite", "Settings", (0.5, 0.62), action="settings")
]

def set_loot_filter(value):
    app.loot_filter_index = loot_filter_levels.index(value)
    if app.show_all_labels:
        assign_label_slots()

loot_filter_dropdown = Dropdown(position=(0.2, 0.20), options=list(loot_filter_levels), on_select=set_loot_filter, get_label=lambda r: r.capitalize() + "+", header_label=lambda r: ["Item Filter ", r.capitalize() + "+"],)

def set_loot_filter_enabled(value):
    app.loot_filter_enabled = value
    if app.show_all_labels:
        assign_label_slots()

loot_filter_checkbox = Checkbox(position=(0.28, 0.20), anchor="center", get_state=lambda: app.loot_filter_enabled, on_toggle=set_loot_filter_enabled)

for b in menu_buttons:
    b.update()
