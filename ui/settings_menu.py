"""THE SETTINGS WINDOW - tabs on the left, the tab's rows on the right.

Open it with the "Settings" button in the Escape menu. Escape closes it again.

A TAB is a name and a function that returns its ROWS:

    def sound_rows():
        return [Header("Volume"), Slider("Master", get_master, set_master)]
    register_settings_tab("sound", "Sound", sound_rows)

The rows are rebuilt every frame, so a tab always shows the current values, and
anything registered later (a new sound folder, a new keybind, a new filter group)
appears by itself.

ROWS you can use:
    Header(text)                              a gold title
    Note(text)                                a small grey line of explanation
    Toggle(label, get, set)                   On / Off
    Choice(label, options, get, set, fmt)     < value >  (click the arrows)
    Slider(label, get, set)                   0 - 100 %, click or drag
    KeyRow(action)                            click, then press the new key
    ActionButton(text, fn)                    a button that runs fn()
    RarityRow()                               the item filter's rarity steps
    GroupRow(group)                           Normal / Always show / Always hide
"""
import pygame
from core.state import app
from core.screen import get_font
from core.assets import draw_window, window_size

# ---------------------------------------------------------------
# LOOK - colours and sizes in one place
# ---------------------------------------------------------------
_TEXT       = (240, 240, 240)
_DIM        = (175, 175, 175)
_NOTE       = (50, 46, 20)     # small explanations - dark, for the light window background
_GOLD       = (240, 200, 90)
_BUTTON     = (45, 42, 30)
_BUTTON_HI  = (80, 72, 45)
_BUTTON_ON  = (110, 92, 40)
_EDGE       = (150, 130, 70)
_GREEN      = (60, 130, 60)
_RED        = (140, 50, 50)
_SLIDER_BAR = (30, 30, 30)

margin = 24            # inside the window's border
tab_width = 170
tab_height = 42
tab_gap = 8
row_height = 38
control_width = 300    # the part of a row right of its label

def _button(rect, text, font, fill=_BUTTON, color=_TEXT, hover=True):
    if hover and rect.collidepoint(pygame.mouse.get_pos()) and fill == _BUTTON:
        fill = _BUTTON_HI
    pygame.draw.rect(app.screen, fill, rect, border_radius=5)
    pygame.draw.rect(app.screen, _EDGE, rect, width=1, border_radius=5)
    label = font.render(text, True, color)
    app.screen.blit(label, label.get_rect(center=rect.center))

def _label(text, rect, font, color=_TEXT):
    surf = font.render(text, True, color)
    app.screen.blit(surf, surf.get_rect(midleft=(rect.left, rect.centery)))

def _control_rect(rect):
    return pygame.Rect(rect.right - control_width, rect.top + 3, control_width, rect.height - 6)

# ---------------------------------------------------------------
# ROWS
# ---------------------------------------------------------------
class Row:
    height = row_height
    def draw(self, rect, ui): pass
    def click(self, pos, ui): return False

class Header(Row):
    height = 44
    def __init__(self, text):
        self.text = text
    def draw(self, rect, ui):
        surf = ui.header_font.render(self.text, True, _GOLD)
        app.screen.blit(surf, surf.get_rect(bottomleft=(rect.left, rect.bottom - 6)))
        pygame.draw.line(app.screen, _EDGE, (rect.left, rect.bottom - 3), (rect.right, rect.bottom - 3), 1)

class Note(Row):
    height = 26
    def __init__(self, text):
        self.text = text
    def draw(self, rect, ui):
        _label(self.text, rect, ui.small_font, _NOTE)

class Toggle(Row):
    def __init__(self, label, get, set):
        self.text, self.get, self.set = label, get, set
    def box(self, rect):
        return pygame.Rect(rect.right - 90, rect.top + 4, 90, rect.height - 8)
    def draw(self, rect, ui):
        _label(self.text, rect, ui.font)
        on = self.get()
        _button(self.box(rect), "On" if on else "Off", ui.font, _GREEN if on else _BUTTON)
    def click(self, pos, ui):
        if ui.last_rects[self].collidepoint(pos):
            self.set(not self.get())
            return True
        return False

class Choice(Row):
    def __init__(self, label, options, get, set, fmt=str):
        self.text, self.options, self.get, self.set, self.fmt = label, list(options), get, set, fmt
    def parts(self, rect):
        c = _control_rect(rect)
        arrow = c.height
        return (pygame.Rect(c.left, c.top, arrow, c.height),
                pygame.Rect(c.left + arrow + 4, c.top, c.width - 2 * arrow - 8, c.height),
                pygame.Rect(c.right - arrow, c.top, arrow, c.height))
    def draw(self, rect, ui):
        _label(self.text, rect, ui.font)
        left, middle, right = self.parts(rect)
        _button(left, "<", ui.font)
        _button(middle, self.fmt(self.get()), ui.font, hover=False)
        _button(right, ">", ui.font)
    def click(self, pos, ui):
        left, _, right = self.parts(ui.last_rects[self])
        step = -1 if left.collidepoint(pos) else 1 if right.collidepoint(pos) else 0
        if not step:
            return False
        current = self.get()
        i = self.options.index(current) if current in self.options else 0
        self.set(self.options[(i + step) % len(self.options)])
        return True

class Slider(Row):
    def __init__(self, label, get, set, on_release=None):
        self.text, self.get, self.set, self.on_release = label, get, set, on_release
    def bar(self, rect):
        c = _control_rect(rect)
        return pygame.Rect(c.left, c.centery - 6, c.width - 70, 12)
    def draw(self, rect, ui):
        _label(self.text, rect, ui.font)
        bar = self.bar(rect)
        value = max(0.0, min(1.0, self.get()))
        pygame.draw.rect(app.screen, _SLIDER_BAR, bar, border_radius=6)
        pygame.draw.rect(app.screen, _GOLD, (bar.left, bar.top, int(bar.width * value), bar.height), border_radius=6)
        pygame.draw.circle(app.screen, _TEXT, (bar.left + int(bar.width * value), bar.centery), 10)
        percent = ui.font.render(f"{round(value * 100)}%", True, _TEXT)
        app.screen.blit(percent, percent.get_rect(midright=(rect.right, rect.centery)))
    def value_at(self, x, bar):
        return max(0.0, min(1.0, (x - bar.left) / max(1, bar.width)))
    def click(self, pos, ui):
        bar = self.bar(ui.last_rects[self]).inflate(20, 20)          # easy to grab
        if not bar.collidepoint(pos):
            return False
        bar = self.bar(ui.last_rects[self])
        self.set(self.value_at(pos[0], bar))
        ui.dragging = (bar, self.set, self.on_release)              # follows the mouse until released
        return True

class KeyRow(Row):
    def __init__(self, action):
        self.action = action
    def draw(self, rect, ui):
        from core.keybinds import actions, key_label
        _label(actions[self.action]["label"], rect, ui.font)
        box = pygame.Rect(rect.right - 160, rect.top + 4, 160, rect.height - 8)
        if ui.capturing == self.action:
            _button(box, "Press a key...", ui.font, _BUTTON_ON, _GOLD)
        else:
            _button(box, key_label(self.action), ui.font)
    def click(self, pos, ui):
        rect = ui.last_rects[self]
        if pygame.Rect(rect.right - 160, rect.top, 160, rect.height).collidepoint(pos):
            ui.capturing = self.action
            return True
        return False

class ActionButton(Row):
    height = 46
    def __init__(self, text, fn):
        self.text, self.fn = text, fn
    def box(self, rect):
        return pygame.Rect(rect.left, rect.top + 6, 240, rect.height - 12)
    def draw(self, rect, ui):
        _button(self.box(rect), self.text, ui.font)
    def click(self, pos, ui):
        if self.box(ui.last_rects[self]).collidepoint(pos):
            self.fn()
            return True
        return False

class RarityRow(Row):
    """One chip per rarity. Click one: that rarity and everything above it is shown."""
    height = 44
    def chips(self, rect):
        from systems.lootfilter import filter_rarities
        w = rect.width // len(filter_rarities)
        return [(r, pygame.Rect(rect.left + i * w, rect.top + 4, w - 4, rect.height - 8))
                for i, r in enumerate(filter_rarities)]
    def draw(self, rect, ui):
        from systems.lootfilter import filter_rarities, filter_rarity
        from systems.rarity import rarity_colors
        chosen = filter_rarities.index(filter_rarity())
        for i, (rarity, chip) in enumerate(self.chips(rect)):
            shown = i >= chosen
            _button(chip, rarity.capitalize(), ui.small_font, _BUTTON_ON if shown else _BUTTON,
                    rarity_colors.get(rarity, _TEXT) if shown else _DIM)
    def click(self, pos, ui):
        from systems.lootfilter import set_filter_rarity
        for rarity, chip in self.chips(ui.last_rects[self]):
            if chip.collidepoint(pos):
                set_filter_rarity(rarity)
                return True
        return False

class GroupRow(Row):
    """Normal (rarity decides) / Always show / Always hide for one filter group."""
    choices = (("normal", "Normal", _BUTTON_ON), ("show", "Show", _GREEN), ("hide", "Hide", _RED))
    def __init__(self, group):
        self.group = group
    def boxes(self, rect):
        w = 96
        right = rect.right
        return [(mode, text, fill, pygame.Rect(right - (3 - i) * (w + 4), rect.top + 4, w, rect.height - 8))
                for i, (mode, text, fill) in enumerate(self.choices)]
    def draw(self, rect, ui):
        from systems.lootfilter import filter_groups, group_mode
        _label(filter_groups[self.group]["label"], rect, ui.font)
        current = group_mode(self.group)
        for mode, text, fill, box in self.boxes(rect):
            chosen = mode == current
            _button(box, text, ui.small_font, fill if chosen else _BUTTON, _TEXT if chosen else _DIM)
    def click(self, pos, ui):
        from systems.lootfilter import set_group_mode
        for mode, _, _, box in self.boxes(ui.last_rects[self]):
            if box.collidepoint(pos):
                set_group_mode(self.group, mode)
                return True
        return False

# ---------------------------------------------------------------
# TABS
# ---------------------------------------------------------------
settings_tabs = []          # (key, label, rows_fn)

def register_settings_tab(key, label, rows_fn):
    settings_tabs.append((key, label, rows_fn))

# ---------------------------------------------------------------
# THE WINDOW
# ---------------------------------------------------------------
class SettingsWindow:
    def __init__(self):
        self.open = False
        self.tab = None
        self.scroll = 0
        self.capturing = None          # an action waiting for its new key
        self.dragging = None           # (bar rect, set fn, on_release) of a slider being dragged
        self.last_rects = {}           # row -> rect, from the last draw (clicks use it)
        self.tab_rects = {}
        self.back_rect = None
        self.content_rect = None

    def show(self):
        self.open = True
        self.scroll = 0
        if self.tab is None and settings_tabs:
            self.tab = settings_tabs[0][0]

    def close(self):
        self.open = False
        self.capturing = None
        self.release()

    def rows(self):
        for key, _, rows_fn in settings_tabs:
            if key == self.tab:
                return rows_fn()
        return []

    def draw(self):
        if not self.open:
            return
        self.font = get_font(22)
        self.small_font = get_font(18)
        self.header_font = get_font(26)

        w, h = window_size("settings")
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (app.screen_width // 2, app.screen_height // 2)
        shade = pygame.Surface((app.screen_width, app.screen_height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 120))
        app.screen.blit(shade, (0, 0))
        draw_window("settings", rect)
        inner = rect.inflate(-margin * 2, -margin * 2)

        # tabs down the left side, a Back button at the bottom
        title = self.header_font.render("Settings", True, _GOLD)
        app.screen.blit(title, (inner.left, inner.top))
        y = inner.top + title.get_height() + 14
        self.tab_rects = {}
        for key, label, _ in settings_tabs:
            tab_rect = pygame.Rect(inner.left, y, tab_width, tab_height)
            self.tab_rects[key] = tab_rect
            _button(tab_rect, label, self.font, _BUTTON_ON if key == self.tab else _BUTTON,
                    _GOLD if key == self.tab else _TEXT)
            y += tab_height + tab_gap
        self.back_rect = pygame.Rect(inner.left, inner.bottom - tab_height, tab_width, tab_height)
        _button(self.back_rect, "Back", self.font)

        # the open tab's rows, scrolled
        content = pygame.Rect(inner.left + tab_width + 24, inner.top, inner.width - tab_width - 24, inner.height)
        self.content_rect = content
        rows = self.rows()
        total = sum(r.height for r in rows)
        self.scroll = max(0, min(self.scroll, total - content.height))
        self.last_rects = {}
        app.screen.set_clip(content)
        y = content.top - self.scroll
        for row in rows:
            row_rect = pygame.Rect(content.left, y, content.width, row.height)
            self.last_rects[row] = row_rect
            if row_rect.bottom > content.top and row_rect.top < content.bottom:
                row.draw(row_rect, self)
            y += row.height
        app.screen.set_clip(None)

        if self.dragging:
            if pygame.mouse.get_pressed()[0]:
                bar, set_fn, _ = self.dragging
                set_fn(max(0.0, min(1.0, (pygame.mouse.get_pos()[0] - bar.left) / max(1, bar.width))))
            else:
                self.release()

    def handle_click(self, pos):
        """Every click while the window is open lands here, so nothing behind it reacts."""
        for key, tab_rect in self.tab_rects.items():
            if tab_rect.collidepoint(pos):
                self.tab, self.scroll, self.capturing = key, 0, None
                return True
        if self.back_rect and self.back_rect.collidepoint(pos):
            self.close()
            return True
        self.capturing = None
        if self.content_rect and self.content_rect.collidepoint(pos):
            for row, rect in list(self.last_rects.items()):
                if rect.collidepoint(pos) and row.click(pos, self):
                    return True
        return True

    def release(self):
        if self.dragging:
            _, _, on_release = self.dragging
            self.dragging = None
            if on_release:
                on_release()

    def handle_wheel(self, amount):
        self.scroll = max(0, self.scroll - amount * 40)

    def handle_key(self, event):
        """True if the window used the key. While waiting for a keybind, it takes every key."""
        if not self.open:
            return False
        if self.capturing and event.type == pygame.KEYDOWN:
            if event.key != pygame.K_ESCAPE:              # Escape cancels: it is never bindable
                from core.keybinds import set_key
                set_key(self.capturing, event.key)
            self.capturing = None
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False

settings_window = SettingsWindow()

# ---------------------------------------------------------------
# THE TABS THEMSELVES - add a row here, or a whole new tab at the bottom.
# ---------------------------------------------------------------
def screen_rows():
    from core.settings import get_setting, set_setting
    from core.screen import window_size_presets, open_window
    from core.events import toggle_fullscreen, on_screen_resized

    def set_size(size):
        set_setting("window_size", list(size))
        if not app.fullscreen:                             # in fullscreen it is used next time you leave it
            open_window(fullscreen=False)
            on_screen_resized()

    return [
        Header("Display"),
        Toggle("Fullscreen", lambda: app.fullscreen, lambda on: toggle_fullscreen()),
        Choice("Window size", window_size_presets, lambda: tuple(get_setting("window_size")), set_size,
               fmt=lambda s: f"{s[0]} x {s[1]}"),
        Note("The window size is used when you are not in fullscreen."),
        Toggle("Show FPS", lambda: get_setting("show_fps"), lambda on: set_setting("show_fps", on)),
    ]

def sound_rows():
    from core.settings import get_setting, set_setting, save_settings
    from core.sounds import all_sound_categories, category_volume

    def set_category(category):
        def set_value(v):
            volumes = dict(get_setting("sound_volumes"))
            volumes[category] = round(v, 3)
            set_setting("sound_volumes", volumes, save=False)
        return set_value

    rows = [Header("Volume"),
            Slider("Master", lambda: get_setting("master_volume"),
                   lambda v: set_setting("master_volume", round(v, 3), save=False), save_settings),
            Header("Per sound folder")]
    for category in all_sound_categories():
        rows.append(Slider(category.replace("_", " ").capitalize(), lambda c=category: category_volume(c),
                           set_category(category), save_settings))
    rows.append(Note("Each folder in assets/sounds gets its own slider."))
    return rows

def keybind_rows():
    from core.keybinds import action_groups, reset_keys
    rows = []
    for group, names in action_groups().items():
        rows.append(Header(group))
        rows += [KeyRow(name) for name in names]
    rows.append(Note("Click a key, then press the new one. Escape cancels."))
    rows.append(ActionButton("Reset all keys", reset_keys))
    return rows

def filter_rows():
    from systems.lootfilter import filter_groups, filter_enabled, set_filter_enabled
    from systems.ground import assign_label_slots

    def set_labels(on):
        app.show_all_labels = on
        if on:
            assign_label_slots()

    return [
        Header("Item filter"),
        Toggle("Item filter on", filter_enabled, set_filter_enabled),
        Note("Show this rarity and everything above it:"),
        RarityRow(),
        Header("Groups"),
        Note("Show always shows it, Hide always hides it. Normal: the rarity decides."),
        *[GroupRow(key) for key in filter_groups],
        Header("Labels"),
        Toggle("Show all item labels", lambda: app.show_all_labels, set_labels),
    ]

register_settings_tab("screen",   "Screen",      screen_rows)
register_settings_tab("sound",    "Sound",       sound_rows)
register_settings_tab("keybinds", "Keybinds",    keybind_rows)
register_settings_tab("filter",   "Item filter", filter_rows)
