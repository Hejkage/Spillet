"""RESOURCES - what abilities spend: mana now, maybe rage/energy later.

A resource is a pool that fills up over time:
    register_resource("mana", "Mana", max_stat="max_mana", regen_stat="mana_regen")

Its max and regen are normal STATS, so items, the skill tree, pet auras and
attributes change them like any other stat.

A gem says what it costs in its template. No "cost" = free:
    "fireball": {..., "cost": {"mana": 12}}
A cost can also go in "rarity_stats", so a legendary version can be cheaper:
    rarity_legendary: {"damage": 50, "cost": {"mana": 8}}

The player keeps the current amounts in player.resources = {"mana": 73.5}.
"""
from systems.items import register_stat

resource_types = {}

def register_resource(name, label, max_stat, regen_stat, max_base=0, regen_base=0,
                      color=(60, 120, 255), back_color=(10, 20, 60)):
    """max_base / regen_base = what the player starts with.
    color / back_color = its bar on the HUD."""
    register_stat(max_stat, f"Maximum {label}", base=max_base, tab="defence", always=True, panel_label=label,
                  as_increase=False)
    register_stat(regen_stat, f"{label} Regen per Second", base=regen_base, tab="defence", always=True)
    resource_types[name] = {"label": label, "max_stat": max_stat, "regen_stat": regen_stat,
                            "color": color, "back_color": back_color}

register_resource("mana", "Mana", max_stat="max_mana", regen_stat="mana_regen",
                  max_base=100, regen_base=5, color=(60, 120, 255), back_color=(10, 20, 60))


# ---------------------------------------------------------------
# HELPERS - used by the player (and later by anything else with resources)
# ---------------------------------------------------------------
def resource_max(owner, name):
    return getattr(owner, resource_types[name]["max_stat"], 0)

def fill_resources(owner):
    """Every resource to full (a new character, respawning)."""
    owner.resources = {name: resource_max(owner, name) for name in resource_types}

def clamp_resources(owner):
    """After the max changed: nothing above the max."""
    current = getattr(owner, "resources", None)
    if current is None:
        fill_resources(owner)
        return
    for name in resource_types:
        current[name] = min(current.get(name, 0), resource_max(owner, name))

def regen_resources(owner, dt):
    for name, config in resource_types.items():
        regen = getattr(owner, config["regen_stat"], 0)
        if regen:
            owner.resources[name] = max(0, min(resource_max(owner, name), owner.resources.get(name, 0) + regen * dt))

def can_pay(owner, cost):
    """cost = {"mana": 12}. None / {} = free."""
    return all(owner.resources.get(name, 0) >= amount for name, amount in (cost or {}).items())

def pay(owner, cost):
    for name, amount in (cost or {}).items():
        owner.resources[name] = owner.resources.get(name, 0) - amount

def describe_cost(cost):
    """{"mana": 12} -> "12 Mana". Empty -> "" (free)."""
    return ", ".join(f"{amount:g} {resource_types[name]['label'] if name in resource_types else name}"
                     for name, amount in (cost or {}).items())
