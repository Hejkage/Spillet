from systems.world_objects import world_object_configs

from core.assets import configure_sprite

configure_sprite("chest_sprite", scale=1, anchor="center", position=(1, 1), pre_scale=2, scale_with_screen=False)

world_object_configs.update({
    "tree": {
        "sprite": "tree_sprite",
        "blocks_movement": True,
        "blocks_projectiles": True,
        "hitbox_size": (64, 32),
        "hitbox_offset": (0, 96)
    },
    "chest": {
        "sprite": "chest_sprite",
        "blocks_movement": True,
        "blocks_projectiles": True,
        "hitbox_size": (119, 64),
        "hitbox_offset": (0, 0)
    },
    "shop": {
        "sprite": "blacksmith_sprite",
        "blocks_movement": True,
        "blocks_projectiles": False,
        "hitbox_size": (64, 64),   
        "hitbox_offset": (0, 0),
    },
})

