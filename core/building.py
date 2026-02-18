from enum import Enum
from dataclasses import dataclass
from core.items import ItemType

class BuildingType(str, Enum):
    HOUSE = "house"
    FARM_PLOT = "farm_plot"
    CAMPFIRE = "campfire"
    STORAGE_BOX = "storage_box"

@dataclass
class BuildingStats:
    max_health: float
    cost: dict[ItemType, int]
    radius: float # Interaction radius
    tick_rate: float = 1.0 # How often update() is called

BUILDING_DB = {
    BuildingType.HOUSE: BuildingStats(
        max_health=500.0,
        cost={ItemType.WOOD: 25, ItemType.STONE: 10},
        radius=15.0
    ),
    BuildingType.FARM_PLOT: BuildingStats(
        max_health=100.0,
        cost={ItemType.WOOD: 5, ItemType.STONE: 5},
        radius=5.0
    ),
    BuildingType.CAMPFIRE: BuildingStats(
        max_health=50.0,
        cost={ItemType.WOOD: 5, ItemType.STONE: 2},
        radius=8.0
    ),
}

class Building:
    def __init__(self, b_type: BuildingType, x: float, y: float, owner_id: int):
        self.type = b_type
        self.x = x
        self.y = y
        self.owner_id = owner_id
        
        stats = BUILDING_DB[b_type]
        self.health = stats.max_health
        self.max_health = stats.max_health
        self.radius = stats.radius
        
        # Specific state
        self.inventory = {} # For storage/farms
        self.timer = 0.0    # For cooldowns (farming/cooking)

    def is_destroyed(self):
        return self.health <= 0

