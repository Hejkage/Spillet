"""HIT ORIGINS - where a hit came from, and what that lets it do.

Every hit knows its origin: "main", "chain", "pierce", "split", "explosion"...

    is_skill=True    the hit IS the skill. Main hit, extra projectiles, chain, pierce.
                     It has everything the skill has and triggers on-hit effects
                     (explode, split, chain, anything from items or trees).

    is_skill=False   the hit is SPAWNED by the skill or an effect. Split projectiles,
                     explosions. It never triggers on-hit effects, so it can't split,
                     chain or explode again. Statuses (slow...) and ailments (burn,
                     poison) still land, and on-kill effects still happen.

What stats a spawned hit uses is decided where it is made, not here:
    split projectile  a copy of the skill's hit: the skill's crit, ailment chances,
                      penetration and leech, with a share of its damage (systems/projectiles.py)
    explosion         YOUR stats only: no gem stats, not an attack or spell (systems/status.py)

A new kind = one register_hit_origin() line, e.g. for a later "echo" or "nova":
    register_hit_origin("echo", is_skill=True)
"""
hit_origins = {}

def register_hit_origin(name, is_skill, label=None):
    hit_origins[name] = {"is_skill": is_skill, "label": label or name.title()}

def is_skill_hit(origin):
    """True if a hit with this origin counts as the skill itself. Unknown = the skill."""
    return hit_origins.get(origin, {"is_skill": True})["is_skill"]

register_hit_origin("main", is_skill=True)        # the hit itself, and extra projectiles
register_hit_origin("chain", is_skill=True)       # a chain bounce
register_hit_origin("pierce", is_skill=True)      # a projectile after it went through an enemy
register_hit_origin("split", is_skill=False)      # the small projectiles from split
register_hit_origin("explosion", is_skill=False)  # explode on hit / on kill
register_hit_origin("burn", is_skill=False)       # damage over time a hit caused.
register_hit_origin("poison", is_skill=False)     # Their kills still trigger that hit's
register_hit_origin("dot", is_skill=False)        # on-kill effects.
