"""Game content: pure data.

Every module here only FILLS registries that systems/ declare.
Systems never import content. Content imports systems.

Order matters where one file refers to another:
  gems -> items -> pets -> world_objects -> drops -> enemies -> shops -> areas
"""
from . import gems
from . import items
from . import pets
from . import world_objects
from . import drops
from . import enemies
from . import shops
from . import areas
from .shops import inventory
