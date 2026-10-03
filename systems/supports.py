import random

from systems.mods import apply_mod, apply_mods, describe_mod, mod_combine, mod_tags, spread_packets

# region Support gems
#
# A support gem is ONE of the things that can use a mod (see systems/mods.py).
# It owns no mechanics of its own: it names a mod, and adds rarity tiers and
# a rolled value on top.

support_gem_types = {}

def register_support_gem(gem_type, name, tiers, mod=None, apply=None, describe=None,
                         tags=None, combine=None):
    """
    mod       the name of a mod in systems/mods.py. The mechanic lives there,
              so a skill tree node or an always-on gem can name the same one.
    apply     only for something nothing else will ever want. Takes the old
              (gem, packets) shape.
    tags      defaults to the mod's own tags, so you rarely write it.
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
        "tags": set(tags) if tags else (set(mod_tags(mod)) if mod else set()),
        "combine": combine if combine is not None else (mod_combine(mod) if mod else "add"),
    }

def combine_support_values(gem_type, values):
    mode = support_gem_types[gem_type].get("combine", "add")
    if mode == "mul":
        total = 1.0
        for v in values:
            total *= v
        return round(total, 3)
    return sum(values)

class SupportGem:
    def __init__(self, gem_type, value, rarity):
        self.gem_type = gem_type
        self.value = value
        self.rarity = rarity
        self.config = support_gem_types[gem_type]
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
         gem accepts their tags (extra["_mod_tags"]).
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
        packets = apply_mods(packets, extra.get("_mods", ()), extra.get("_mod_tags"))

    for gem in support_gems:
        packets = gem.apply_gem(packets)
    return packets

# the old name, so nothing breaks while you rename the call sites
apply_support_gems = build_hit_packets
#endregion