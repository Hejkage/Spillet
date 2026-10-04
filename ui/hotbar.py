import pygame
from core.state import app
from core.screen import get_font
from core.assets import get_ui_scaled
from systems.items import active_gem_slots, equipment, hover_state

# region Hotbar

hotbar_slot_size = 56
hotbar_padding = 8

hotbar_slots = [("primary", "MB1")] + [(slot, str(i + 1)) for i, slot in enumerate(active_gem_slots)]
ability_keybinds = {slot: getattr(pygame, f"K_{i + 1}") for i, slot in enumerate(active_gem_slots)}

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
            if icon_name is None and ability_key != "primary":
                gem_item = equipment.extra_slots.get(ability_key)
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

def ability_tooltip_lines(ability, player):
    """The lines describing one ability. Used by the hotbar tooltip AND by the
    gem item tooltip, so the two can never drift apart.
    Returns [(text, colour), ...]. A stat the ability does not have is left out."""
    from systems.damage import damage_colors
    stats = ability.get_effective_stats(player)
    white = (255, 255, 255)
    lines = [(ability.name, (255, 220, 120))]

    lines.append((f"Damage: {stats['damage']:.0f}", white))

    for damage_type, amount in sorted(stats["parts"].items(), key=lambda kv: -kv[1]):
        lines.append((f"  {damage_type.title()}: {amount:.0f}", damage_colors.get(damage_type, white)))

    if stats["projectiles"] > 1:
        lines.append((f"Projectiles: {stats['projectiles']}", white))

    if ability.speed_stat:                  # an attack: shown as a rate
        rate = 1 / stats["cooldown"] if stats["cooldown"] > 0 else 0
        lines.append((f"Attack speed: {rate:.2f} per second", white))
        lines.append((f"Attack time: {stats['cooldown']:.2f}s", white))
    else:
        lines.append((f"Cooldown: {stats['cooldown']:.2f}s", white))
    if ability.action_time:
        lines.append((f"Cast time: {ability.action_time:.2f}s", white))

    chance, crit_damage = player.crit_stats(stats["hit_stats"])
    if chance > 0:
        lines.append((f"Crit chance: {min(100, chance):.1f}%", white))
    if crit_damage > 0:
        lines.append((f"Crit damage: {crit_damage:.0f}%", white))

    if stats["dot_damage"] > 0:
        lines.append((f"Damage over time: {stats['dot_damage']:.0f} per second", white))
        if stats["dot_duration"] > 0:
            lines.append((f"DoT duration: {stats['dot_duration']:.0f}s", white))

    if stats["hit_kind"] == "melee":
        lines.append((f"Range: {stats['range']:.0f}", white))
        if stats["arc"]:
            lines.append((f"Swing arc: {stats['arc']:.0f} degrees", white))
    else:
        lines.append((f"Projectile speed: {stats['speed']:.0f}", white))

    if stats["uses_aoe"]:
        lines.append((f"Area of effect: {stats['aoe'] * 100:.0f}%", white))
    if stats.get("orbit_range", 0) > 0:
        lines.append((f"Orbits you at {stats['orbit_range']:.0f} range", white))
    if stats["hit_stats"].get("pierce"):
        lines.append((f"Pierces {int(stats['hit_stats']['pierce'])} targets", white))

    # socketed support gems only. What the gem TREE gives is the tree's own screen.
    supports = [g for g in ability.support_gems if not getattr(g, "from_tree", False)]
    if supports:
        lines.append(("", white))
        for gem in supports:
            lines.append((f"- {gem.gem_name}: {gem.describe()}", white))

    return lines

    return lines

def draw_ability_tooltip(player):
    from systems.items import draw_tooltip_box
    ability = hover_state.ability
    if not ability:
        return
    draw_tooltip_box(ability_tooltip_lines(ability, player))
