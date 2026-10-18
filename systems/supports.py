import random

from systems.mods import apply_mod, apply_mods, describe_mod, mod_combine, mod_needs, mod_scales, spread_packets

# region Support gems
#
# A support gem is ONE of the things that can use a mod (see systems/mods.py).
# It owns no mechanics of its own: it names a mod, and adds rarity tiers and
# a rolled value on top.

support_gem_types = {}

def register_support_gem(gem_type, name, tiers, mod=None, apply=None, describe=None,
                         needs=None, combine=None):
    """
    mod       the name of a mod in systems/mods.py. The mechanic lives there,
              so a skill tree node or an always-on gem can name the same one.
    apply     only for something nothing else will ever want. Takes the old
              (gem, packets) shape.
    needs     tags a skill must ALL have to take this support (systems/tags.py).
              Defaults to the mod's own needs, so you rarely write it.
    describe  defaults to the mod's own description.
    combine   defaults to the mod's own setting. Only used by the gem tree UI.
    """
    if mod is None and apply is None:
        raise ValueError(f"Support gem '{gem_type}' needs either mod= or apply=")
    support_gem_types[gem_type] = {
        "name": name,
        "tiers": tiers,
        "mod": mod,
        "apply": apply,
        "describe": describe,
        "needs": set(needs) if needs else (set(mod_needs(mod)) if mod else set()),
        "scales": set(mod_scales(mod)) if mod else set(),
        "combine": combine if combine is not None else (mod_combine(mod) if mod else "add"),
    }

def support_fits(gem_type, ability_tags, blocked=()):
    """Can this support type be used on an ability with these tags? The ONE check
    used by socketing, the gem tree, built-in supports and rebuilding abilities."""
    from systems.tags import fits
    config = support_gem_types[gem_type]
    return fits(config["needs"], config["scales"], ability_tags, blocked)

def combine_support_values(gem_type, values):
    from systems.mods import combine_values
    config = support_gem_types[gem_type]
    return combine_values(config["mod"], values) if config["mod"] else sum(values)

class SupportGem:
    def __init__(self, gem_type, value, rarity):
        self.gem_type = gem_type
        self.config = support_gem_types[gem_type]
        from systems.mods import mod_combine
        if self.config["mod"] and mod_combine(self.config["mod"]) == "more" and 0 < value < 5:
            value = round((value - 1) * 100, 2)      # an old save: 1.25 (x1.25) is now 25 (25% more)
        self.value = value
        self.rarity = rarity
        self.gem_name = self.config["name"]

    def apply_gem(self, packets):
        if self.config["mod"]:
            return apply_mod(self.config["mod"], packets, self.value)
        return self.config["apply"](self, packets)

    def describe(self):
        if self.config["describe"]:
            return self.config["describe"](self)
        return describe_mod(self.config["mod"], self.value)

def roll_support_value(gem_type, rarity):
    low, high = support_gem_types[gem_type]["tiers"][rarity]
    if isinstance(low, int) and isinstance(high, int):
        return random.randint(low, high)
    return round(random.uniform(low, high), 2)

def build_hit_packets(base_direction, base_speed, base_damage, base_aoe, sprite_name,
                      support_gems, extra=None, count=1):
    """Build the hit packets for one cast of one ability.

    A projectile spawns from each packet; a melee swing reads the first.

    Order:
      1. the packet is laid out (one, a fan, or a cone)
      2. the gem's own "always" mods (extra["_always"]), which you chose
         yourself so they are not filtered, then mods from OUTSIDE the gem
         (extra["_mods"]: the skill tree, uniques), which only apply if the
         ability has every tag they need (extra["tags"], see systems/tags.py).
      3. the support gems sitting in its sockets
    """
    packet = {
        "direction": base_direction,
        "base_direction": base_direction,
        "speed": base_speed,
        "damage": base_damage,
        "aoe": base_aoe,
        "sprite": sprite_name,
    }
    if extra:
        packet.update(extra)

    packets = spread_packets(packet, extra.get("_count", count) if extra else count)

    if extra:
        packets = apply_mods(packets, extra.get("_always", ()), None)
        packets = apply_mods(packets, extra.get("_mods", ()), extra.get("tags", set()), extra.get("blocked", ()))

    for gem in support_gems:
        packets = gem.apply_gem(packets)

    # 4. effects from the gem's tree and from your items ("on_hit" / "on_kill")
    for event, effects in (extra or {}).get("_events", {}).items():
        field = "effects" if event == "on_hit" else event
        for p in packets:
            p[field] = list(p.get(field, ())) + list(effects)

    # 5. only now the real numbers: damage (flat, then increased, then more),
    #    and projectile speed / area with what the hit carries added to yours
    if extra and "_stat" in extra:
        from systems.damage import finish_hit_damage
        stat = extra["_stat"]
        finish_hit_damage(packets, base_damage, stat)
        for player_stat, key in hit_scaled_stats:
            yours = stat(player_stat, 100, None)
            for p in packets:
                with_hit = stat(player_stat, 100, p)
                if yours and with_hit != yours:
                    p[key] = p[key] * with_hit / yours
    return packets

# Stats that are already in a packet's numbers before mods run (speed, aoe). A mod
# like ("increased_projectile_speed", 20) on a gem is added to YOUR stat at the end.
hit_scaled_stats = [("projectile_speed", "speed"), ("aoe", "aoe")]
# the old name, so nothing breaks while you rename the call sites
apply_support_gems = build_hit_packets
#endregion