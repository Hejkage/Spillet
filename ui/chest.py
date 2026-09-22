from core.state import world
from systems.player import MoveOrder, player
from ui.panels import GridContainer, open_center_panel

# NOTE: imports for the modules below are done inside the functions that
# need them, because those modules are created after this one.

# region Chest
chest_columns = 8
chest_rows = 5
chest_slot_size = 64
chest_padding = 4

class Chest(GridContainer):
    source_kind = "chest"
    base_slot_size = chest_slot_size
    base_padding = chest_padding

    def __init__(self, cols=chest_columns, rows=chest_rows):
        super().__init__(cols, rows)

chest = Chest()

def try_click_container_object(pos):
    from content import inventory
    for o in world.world_objects:
        container = getattr(o, "linked_container", None)
        if container is None:
            continue
        if o.sprite_rect.collidepoint(pos):
            dx = o.x - player.x
            dy = o.y - player.y
            if (dx * dx + dy * dy) ** 0.5 <= o.use_radius:
                if container.open:
                    open_center_panel(None)
                    inventory.open = False
                else:
                    open_center_panel(container)
                    inventory.open = True
                player.move_target = None
            else:
                player.move_target = make_open_container_order(o, container, o.use_radius)
            return True
    return False

def try_shift_transfer(pos):
    from content import inventory
    if not chest.open:
        return False

    inv_bag = inventory.bags[0]
    chest_bag = chest.bags[0]

    i = inventory.slot_index_at(pos)
    if i is not None:
        item = inv_bag.slots[i]
        if item is not None and chest_bag.add_item(item):
            inv_bag.slots[i] = None
        return True
    
    j = chest.slot_index_at(pos)
    if j is not None:
        item = chest_bag.slots[j]
        if item is not None and inv_bag.add_item(item):
            chest_bag.slots[j] = None
        return True

    return False

def make_open_container_order(world_obj, container, radius):
    from content import inventory
    def on_arrive():
        open_center_panel(container)
        inventory.open = True
    return MoveOrder(world_obj, radius, on_arrive, is_valid=lambda: world_obj in world.world_objects)
