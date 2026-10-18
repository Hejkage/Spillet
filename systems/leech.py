"""LEECH - life (and mana) back from the damage your hits deal.

    lifesteal            ATTACKS only. That % of the damage dealt comes back as life.
    spell_leech          SPELLS only. That % of the damage dealt comes back, shared
                         between life and mana by spell_leech_to_mana.
    spell_leech_to_mana  how much of spell leech goes to mana. Starts at 50 (half).
                         A node with ("spell_leech_to_mana", 50) makes it 100:
                         "All life leeched via spell leech is converted to mana".
                         ("spell_leech_to_mana", -50) makes it 0: all life.

Explosions, burning ground and other effects are neither attacks nor spells,
so they never leech. Split projectiles are the same attack/spell as their skill,
so they leech like it.

A new kind of leech = one row in leech_rules, e.g. mana from attacks:
    ("attack", "attack_mana_leech", "attack_mana_leech_to_mana")   with that stat's base at 100
"""
from systems.items import register_stat

register_stat("spell_leech", "Spell Leech", base=0, tab="misc", percent=True)
register_stat("spell_leech_to_mana", "Spell Leech to Mana", base=50, percent=True, show_in_panel=False)

# (hit_type, leech stat, stat for the share that goes to mana - None = all life)
leech_rules = [
    ("attack", "lifesteal",   None),
    ("spell",  "spell_leech", "spell_leech_to_mana"),
]

def leech(attacker, hit_stats, damage):
    """Called once for every hit that lands, with the damage it dealt."""
    if damage <= 0 or not hasattr(attacker, "resolve_stat"):      # pets don't leech (yet)
        return
    hit_type = (hit_stats or {}).get("hit_type")
    for rule_type, stat, mana_stat in leech_rules:
        if hit_type != rule_type:
            continue
        amount = damage * attacker.resolve_stat(stat, hit_stats) / 100
        if amount <= 0:
            continue
        to_mana = 0
        if mana_stat:
            to_mana = min(100, max(0, attacker.resolve_stat(mana_stat, hit_stats))) / 100
        if to_mana < 1:
            attacker.heal(amount * (1 - to_mana))
        if to_mana > 0:
            from systems.resources import gain_resource
            gain_resource(attacker, "mana", amount * to_mana)
