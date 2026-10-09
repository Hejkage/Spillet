import pygame
from core.state import app
from core.screen import get_font
from core.assets import get_ui_scaled
from systems.items import active_gem_slots, equipment, hover_state

# region Hotbar

hotbar_slot_size = 56
hotbar_slot_size = 56
hotbar_padding = 8

# Pets: a column on the LEFT of the screen, from the top down. When the column
# reaches the HUD at the bottom, the next pets start a new column to the right.
pet_bar_left = 12        # distance from the left edge
pet_bar_top = 50         # distance from the top (below the FPS counter)

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

    draw_pet_slots(player, slot_size, padding)

def pet_slot_rect(index, slot_size, padding):
    """Where pet number `index` goes: down the left side, then the next column."""
    from core.screen import hud_height
    scale = app.ui_scale
    top = int(pet_bar_top * scale)
    bottom = app.screen_height - int(hud_height * scale)
    per_column = max(1, (bottom - top + padding) // (slot_size + padding))
    column, row = divmod(index, per_column)
    x = int(pet_bar_left * scale) + column * (slot_size + padding)
    y = top + row * (slot_size + padding)
    return pygame.Rect(x, y, slot_size, slot_size)

def draw_pet_slots(player, slot_size, padding):
    """Your pets, down the left side. Hover one to see its REAL
    stats (gear, its tree and auras included) - like an ability."""
    from core.assets import scaled_sprites
    from systems.items import scale_item_sprite
    from systems.rarity import rarity_colors
    background = get_ui_scaled("inventory_slot_sprite", slot_size, slot_size)
    for i, pet in enumerate(player.pets):
        rect = pet_slot_rect(i, slot_size, padding)
        if background:
            app.screen.blit(background, rect)
        icon = scale_item_sprite(scaled_sprites[pet.sprite_name], slot_size * 0.8)
        app.screen.blit(icon, icon.get_rect(center=rect.center))

        if pet.get_stat("ability") and pet.ability_timer > 0:
            ratio = min(1.0, pet.ability_timer / max(0.01, pet.ability_cooldown()))
            overlay_height = int(slot_size * ratio)
            overlay = pygame.Surface((slot_size, overlay_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            app.screen.blit(overlay, (rect.x, rect.bottom - overlay_height))

        pygame.draw.rect(app.screen, rarity_colors.get(pet.rarity, (255, 255, 255)), rect, 2)
        if rect.collidepoint(pygame.mouse.get_pos()):
            hover_state.pet = pet

def ailment_tooltip_lines(player, stats):
    """Burn / poison for one ability: only the TOTAL chance (player + gem + tree + supports).
    How long and how hard they hit are player stats, shown in the stats panel."""
    from systems.ailments import attacker_value, ailment_types
    from systems.status import status_effect_types
    lines = []
    for name in ailment_types:
        chance = attacker_value(player, f"{name}_chance", stats["hit_stats"])
        if chance > 0:
            lines.append((f"Chance to {name}: {min(100, chance):g}%", status_effect_types[name]["color"]))
    return lines

def ability_tooltip_lines(ability, player):
    """The lines describing one ability. Used by the hotbar tooltip AND by the
    gem item tooltip, so the two can never drift apart.
    Returns [(text, colour), ...]. A stat the ability does not have is left out."""
    from systems.damage import damage_colors
    stats = ability.get_effective_stats(player)
    white = (255, 255, 255)
    lines = [(ability.name, (255, 220, 120))]

    from systems.damage import damage_lines
    lines.extend(damage_lines(stats["parts"]))

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

    lines.extend(ailment_tooltip_lines(player, stats))

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

def draw_ability_tooltip(player):
    from systems.items import draw_tooltip_box
    if hover_state.ability:
        draw_tooltip_box(ability_tooltip_lines(hover_state.ability, player))
    elif hover_state.pet:
        from systems.pets import pet_live_tooltip_lines
        draw_tooltip_box(pet_live_tooltip_lines(hover_state.pet))
