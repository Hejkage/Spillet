
# region Status effects
status_effect_types = {}

def register_status(name, apply=None, tick=None, expire=None):
    status_effect_types[name] = {"apply": apply, "tick": tick, "expire": expire}

def slow_apply(enemy, status):
    enemy.slow_multiplier = 1.0 - status.get("amount", 0)

def slow_expire(enemy, status):
    enemy.slow_multiplier = 1.0

def dot_tick(enemy, status, dt):
    enemy.enemy_take_damage(status.get("dps", 0) * dt)

register_status("slow", apply=slow_apply, expire=slow_expire)
register_status("dot", tick=dot_tick)
register_status("silence")   
