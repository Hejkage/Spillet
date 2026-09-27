from systems.skilltree import register_skill_node, register_skill_edge

register_skill_node("start", "Origin", position=(800, 800), is_root=True)

register_skill_node("vitality_1", "Vitality I", position=(550, 600),
    stats=[{"stat": "max_health", "amount": 50, "type": "flat"}])
register_skill_node("vitality_2", "Vitality II", position=(550, 400),
    stats=[{"stat": "max_health", "amount": 50, "type": "flat"}])

register_skill_node("swiftness_1", "Swiftness I", position=(1050, 600),
    stats=[{"stat": "movement_speed", "amount": 20, "type": "flat"}])
register_skill_node("swiftness_2", "Swiftness II", position=(1050, 400),
    stats=[{"stat": "movement_speed", "amount": 20, "type": "flat"}])

register_skill_edge("start", "vitality_1")
register_skill_edge("vitality_1", "vitality_2")
register_skill_edge("start", "swiftness_1")
register_skill_edge("swiftness_1", "swiftness_2")
register_skill_edge("vitality_2", "swiftness_2") 