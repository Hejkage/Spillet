from systems.gemtree import register_gem_node, register_gem_edge

register_gem_node("fireball", "start", "Ember Core", position=(800, 800), is_root=True)
register_gem_node("fireball", "dmg_1", "Kindling", position=(600, 620), support_type="damage", value=1.12)
register_gem_node("fireball", "dmg_2", "Conflagration", position=(600, 420), support_type="damage", value=1.18)
register_gem_node("fireball", "aoe_1", "Wide Blast", position=(1000, 620), support_type="aoe", value=1.15)
register_gem_node("fireball", "aoe_2", "Firestorm", position=(1000, 420), support_type="aoe", value=1.25)
register_gem_node("fireball", "proj_1", "Split Flame", position=(800, 300), support_type="projectiles", value=2)
register_gem_node("fireball", "crit_1", "Searing Focus", position=(800, 950), support_type="crit_chance", value=80)
register_gem_node("fireball", "socket_1", "Socket", position=(400, 800), is_socket=True)
register_gem_node("fireball", "socket_2", "Socket", position=(1200, 800), is_socket=True)
register_gem_node("fireball", "burn_1", "Smoulder", position=(1000, 950), support_type="burn_chance", value=5)



register_gem_edge("fireball", "start", "burn_1")
register_gem_edge("fireball", "start", "dmg_1")
register_gem_edge("fireball", "dmg_1", "dmg_2")
register_gem_edge("fireball", "start", "aoe_1")
register_gem_edge("fireball", "aoe_1", "aoe_2")
register_gem_edge("fireball", "dmg_2", "proj_1")
register_gem_edge("fireball", "aoe_2", "proj_1")
register_gem_edge("fireball", "start", "crit_1")
register_gem_edge("fireball", "start", "socket_1")
register_gem_edge("fireball", "start", "socket_2")
###################################################################################################################################

register_gem_node("shotgun_blast", "start", "Test socket", position=(800, 800), is_root=True)
register_gem_node("shotgun_blast", "dmg_1", "Kindling", position=(600, 620), is_socket=True)

register_gem_edge("shotgun_blast", "start", "dmg_1")