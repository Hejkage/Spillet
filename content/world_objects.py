from systems.world_objects import world_object_configs
from core.assets import configure_sprite

configure_sprite("chest_sprite", scale=1, anchor="center", position=(1, 1), pre_scale=2, scale_with_screen=False)
configure_sprite("boulder_sprite", scale=2, anchor="center", position=(1, 1), pre_scale=1, scale_with_screen=False)

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

    "boulder": {
            "sprite": "boulder_sprite",
            "blocks_movement": True,
            "blocks_projectiles": True,
            "hitbox_size": (128, 48),
            "hitbox_offset": (0, 48)
        },

    "grass_one": {
            "sprite": "grass_one_sprite",
            "blocks_movement": False,
            "blocks_projectiles": False,
            "hitbox_size": (64, 64),
            "hitbox_offset": (0, 0)
        },

    "grass_two": {
                "sprite": "grass_two_sprite",
                "blocks_movement": False,
                "blocks_projectiles": False,
                "hitbox_size": (64, 64),
                "hitbox_offset": (0, 0)
            },

    "grass_three": {
                "sprite": "grass_three_sprite",
                "blocks_movement": False,
                "blocks_projectiles": False,
                "hitbox_size": (64, 64),
                "hitbox_offset": (0, 0)
            },

    "medium_rock": {
                "sprite": "medium_rock_sprite",
                "blocks_movement": True,
                "blocks_projectiles": False,
                "hitbox_size": (100, 16),
                "hitbox_offset": (0, -14)
            },

    "small_rock": {
                    "sprite": "small_rock_sprite",
                    "blocks_movement": True,
                    "blocks_projectiles": False,
                    "hitbox_size": (40, 8),
                    "hitbox_offset": (0, -7)
                },
})

