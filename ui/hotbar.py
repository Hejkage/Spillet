import pygame
from core.state import app
from core.screen import get_font
from core.assets import get_ui_scaled
from systems.items import active_gem_slot, equipment, hover_state

# region Hotbar

hotbar_slot_size = 56
hotbar_padding = 8

hotbar_slots = [
    ("primary", "MB1"),
    ("main", "1"),
]

ability_keybinds = {
    "main": pygame.K_1,
}

app.hotbar_rects = {}

def draw_hotbar(player):
    app.hotbar_rects = {}

    scale = app.ui_scale
    slot_size = max(1, int(hotbar_slot_size * scale))
    padding = max(1, int(hotbar_padding * scale))

    total_width = len(hotbar_slots) * slot_size + (len(hotbar_slots) - 1) * padding
    start_x = app.screen_width // 2 - total_width // 2
    y = app.screen_height - slot_size - int(60 * scale)

    font = get_font(max(14, int(18 * scale)))

    for i, (ability_key, key_label) in enumerate(hotbar_slots):
        x = start_x + i * (slot_size + padding)
        rect = pygame.Rect(x, y, slot_size, slot_size)
        app.hotbar_rects[ability_key] = rect

        ability = player.abilities.get(ability_key)

        icon_name = None
        if ability:
            icon_name = ability.icon_name
            if icon_name is None and ability_key == "main":
                gem_item = equipment.extra_slots.get(active_gem_slot)
                icon_name = gem_item.sprite_name if gem_item else None

        art = get_ui_scaled(icon_name, slot_size, slot_size) if icon_name else None
        if art is None:
            art = get_ui_scaled("inventory_slot_sprite", slot_size, slot_size)

        if art:
            app.screen.blit(art, rect)

        if ability and ability.timer > 0:
            base = ability.get_base_effective(player)
            ratio = min(1.0, ability.timer / base["cooldown"]) if base["cooldown"] > 0 else 0
            overlay_height = int(slot_size * ratio)
            overlay = pygame.Surface((slot_size, overlay_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            app.screen.blit(overlay, (rect.x, rect.bottom - overlay_height))

        label = font.render(key_label, True, (255, 255, 255))
        app.screen.blit(label, (rect.x + int(4 * scale), rect.y + int(2 * scale)))

        if rect.collidepoint(pygame.mouse.get_pos()) and ability:
            hover_state.ability = ability

def draw_ability_tooltip(player):
    ability = hover_state.ability
    if not ability:
        return
    
    scale = app.ui_scale
    font_size = max(16, int(20 * scale))
    font = get_font(font_size)

    stats = ability.get_effective_stats(player)

    lines = [ability.name]
    lines.append(f"Damage: {stats['damage']:.0f}")

    if ability.speed_stat:
        lines.append(f"Attack time: {stats['cooldown']:.2f}s")
    else:
        lines.append(f"Cooldown: {stats['cooldown']:.2f}s")

    if stats["hit_kind"] == "melee":
        lines.append(f"DPS (single target): {stats['dps']:.0f}")
        lines.append(f"Range: {stats['range']:.0f}")
    else:
        if stats["projectiles"] > 0:
            lines.append(f"Projectiles: {stats['projectiles']}")
            lines.append(f"Damage per cast: {stats['damage'] * stats['projectiles']:.0f}")
        lines.append(f"DPS: {stats['dps']:.0f}")
        lines.append(f"Projectile speed: {stats['speed']:.0f}")

    if stats["uses_aoe"]:
        lines.append(f"Area: {stats['aoe'] * 100 :.0f}%")

    if stats.get("orbit_range", 0) > 0:
        lines.append(f"Projectiles orbit at {stats['orbit_range']:.0f} range")

    total_cc, total_cd = player.crit_stats(stats["hit_stats"])
    if total_cc > 0:
        lines.append(f"Crit chance: {min(100, total_cc):.1f}%")
    if total_cd > 0:
        lines.append(f"Crit damage: {total_cd:.0f}%")
    
    if stats["dot_damage"] > 0:
        lines.append(f"DoT: {stats['dot_damage']:.0f} /s")
        lines.append(f"DoT duration: {stats['dot_duration']:.0f}s")

    if ability.support_gems:
        lines.append("")
        for gem in ability.support_gems:
            lines.append(f"- {gem.gem_name}: {gem.describe()}")

    rendered = [font.render(line, True, (255, 255, 255) if i else (255, 220, 120)) for i, line in enumerate(lines)]

    padding = 10
    width = max(t.get_width() for t in rendered) + padding * 2
    height = sum(t.get_height() for t in rendered) + padding * 2

    mouse_x, mouse_y = pygame.mouse.get_pos()
    box_x = min(mouse_x + 20, app.screen_width - width)
    box_y = max(0, mouse_y - height)

    box_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    box_surface.fill((20, 20, 20, 230))
    app.screen.blit(box_surface, (box_x, box_y))

    y_offset = box_y + padding
    for t in rendered:
        app.screen.blit(t, (box_x + padding, y_offset))
        y_offset += t.get_height()

