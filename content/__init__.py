"""Game content: pure data.

Every module here only FILLS registries that systems/ declare.
Systems never import content. Content imports systems.

Order matters where one file refers to another at load time. For example
drops.py copies pet_group into its drop pools, so pets/ must load first.

load_folder("pets") loads EVERY file in content/pets/ (alphabetically), so a new
pet is just a new file - nothing to add here. Same for content/uniques/. Files starting with _ are skipped.
To give another kind of content its own folder later (enemies, items...), move
its .py file into a folder of the same name and swap the import for load_folder.
"""
import importlib
import pkgutil
from pathlib import Path

def load_folder(folder):
    path = Path(__file__).parent / folder
    importlib.import_module(f"{__name__}.{folder}")
    for mod in sorted(pkgutil.iter_modules([str(path)]), key=lambda m: m.name):
        if not mod.name.startswith("_"):
            importlib.import_module(f"{__name__}.{folder}.{mod.name}")

from . import gems
from . import gem_trees
from . import items
load_folder("pets")
load_folder("uniques")
from . import world_objects
from . import drops
from . import enemies
from . import shops
from . import monsters
from . import packs
load_folder("areas")
from .shops import inventory
from . import skilltree
# Every tag, defence key and immunity in content/ is checked once, now that it
# has all loaded. A typo stops the game here with a list of what is wrong.
from systems.tags import check_all_content
check_all_content()