import random

# region support gems
#support gem modifiers
projectile_spread_angle = 15 #Projectiles support

support_gem_types = {}

def register_support_gem(gem_type, name, tiers, apply, describe, tags=None, combine="add"):
    support_gem_types[gem_type] = {
        "name": name,
        "tiers": tiers,
        "apply": apply,
        "describe": describe,
        "tags": set(tags) if tags else set(),
        "combine": combine,
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

    def apply_gem(self, projectile_list):
        return self.config["apply"](self, projectile_list)
    
    def describe(self):
        return self.config["describe"](self)
    
def roll_support_value(gem_type, rarity):
    low, high = support_gem_types[gem_type]["tiers"][rarity]
    if isinstance(low, int) and isinstance(high, int):
        return random.randint(low, high)
    return round(random.uniform(low, high), 2)

def spread_projectiles(base, count):
    if count <= 1:
        return [base]
    base_dir = base["base_direction"]
    start = -(count - 1) / 2
    return [{**base, "direction": base_dir.rotate((start + i) * projectile_spread_angle)}
            for i in range(count)]

def apply_support_gems(base_direction, base_speed, base_damage, base_aoe, sprite_name, support_gems, extra=None, count=1):
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

    projectile_list = spread_projectiles(packet, extra.get("_count", count) if extra else count)

    for gem in support_gems:
        projectile_list = gem.apply_gem(projectile_list)
    return projectile_list

def scale_key(key):
    def apply(gem, projectile_list):
        for p in projectile_list:
            p[key] = p.get(key, 0) * gem.value
        return projectile_list
    return apply

def multiply_projectiles(gem, projectile_list):
    return spread_projectiles(projectile_list[0], len(projectile_list) + gem.value)

def burst_fire(gem, projectile_list):
    extra = int(gem.value)
    cooldown_mult = 1.5 + (extra - 1) * 0.25
    for p in projectile_list:
        p["cooldown_mult"] = p.get("cooldown_mult", 1.0) * cooldown_mult
        p["burst_extra"] = p.get("burst_extra", 0) + extra
        p["burst_interval"] = 0.05
    return projectile_list

def add_pierce(gem, projectile_list):
    for p in projectile_list:
        p["pierce"] = p.get("pierce", 0) + int(gem.value)
    return projectile_list

def add_crit_damage(gem, projectile_list):
    for p in projectile_list:
        p["crit_damage"] = p.get("crit_damage", 0) + gem.value
    return projectile_list

def add_increased_crit_chance(gem, projectile_list):
    for p in projectile_list:
        key = "spell_crit_chance_increase" if p.get("crit_type", "attack") == "spell" else "attack_crit_chance_increase"
        p[key] = p.get(key, 0) + gem.value
    return projectile_list

def add_increased_attack_speed(gem, projectile_list):
    for p in projectile_list:
        p["cooldown_mult"] = p.get("cooldown_mult", 1.0) / (1 + gem.value / 100)
    return projectile_list

def apply_orbit(gem, projectile_list):
    for p in projectile_list:
        p["orbit"] = True
        p["orbit_radius"] = p.get("orbit_radius", 0) + gem.value               
    return projectile_list
