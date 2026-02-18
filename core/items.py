from enum import Enum
from dataclasses import dataclass

class ItemType(str, Enum):
    # Resources
    WOOD = "wood"
    STONE = "stone"
    COPPER_ORE = "copper_ore"
    IRON_ORE = "iron_ore"
    COAL = "coal" # For smelting
    MEAT = "meat"
    LEATHER = "leather"
    
    # Consumables
    COOKED_MEAT = "cooked_meat"
    HEALING_HERB = "healing_herb"
    
    # Processed Resources
    COPPER_INGOT = "copper_ingot"
    IRON_INGOT = "iron_ingot"
    
    # Tools
    STONE_PICKAXE = "stone_pickaxe"
    COPPER_PICKAXE = "copper_pickaxe"
    IRON_PICKAXE = "iron_pickaxe"
    
    # Weapons
    STONE_SPEAR = "stone_spear"
    COPPER_SPEAR = "copper_spear"
    IRON_SPEAR = "iron_spear"
    
    # Armor / Storage
    LEATHER_BAG = "leather_bag"   # Increases max weight
    LEATHER_ARMOR = "leather_armor" # Reduces damage taken

class ItemCategory(str, Enum):
    RESOURCE = "resource"
    TOOL = "tool"
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    OTHER = "other"

@dataclass
class ItemStats:
    weight: float = 0.1
    max_stack: int = 64
    category: ItemCategory = ItemCategory.RESOURCE
    # Weapon/Tool stats
    damage: float = 0.0
    efficiency: float = 1.0  # Mining speed multiplier
    durability: float = 100.0
    # Armor/Bag stats
    defense: float = 0.0
    carry_bonus: float = 0.0
    # Consumable stats
    energy_gain: float = 0.0
    heal_amount: float = 0.0

# Database of item properties
ITEM_DB = {
    # --- Resources ---
    ItemType.WOOD: ItemStats(weight=0.5, category=ItemCategory.RESOURCE),
    ItemType.STONE: ItemStats(weight=1.0, category=ItemCategory.RESOURCE),
    ItemType.COPPER_ORE: ItemStats(weight=1.2, category=ItemCategory.RESOURCE),
    ItemType.IRON_ORE: ItemStats(weight=1.5, category=ItemCategory.RESOURCE),
    ItemType.MEAT: ItemStats(weight=0.2, category=ItemCategory.CONSUMABLE, energy_gain=25.0),
    ItemType.LEATHER: ItemStats(weight=0.1, category=ItemCategory.RESOURCE),
    
    # --- Consumables ---
    ItemType.COOKED_MEAT: ItemStats(
        weight=0.2, category=ItemCategory.CONSUMABLE, 
        energy_gain=60.0, heal_amount=10.0
    ),
    ItemType.HEALING_HERB: ItemStats(
        weight=0.1, category=ItemCategory.CONSUMABLE, 
        heal_amount=35.0, energy_gain=5.0
    ),
    
    ItemType.COPPER_INGOT: ItemStats(weight=1.0, category=ItemCategory.RESOURCE),
    ItemType.IRON_INGOT: ItemStats(weight=1.3, category=ItemCategory.RESOURCE),
    
    # --- Tools (Pickaxes increase gathering speed) ---
    ItemType.STONE_PICKAXE: ItemStats(
        weight=2.0, max_stack=1, category=ItemCategory.TOOL,
        damage=5.0, efficiency=1.5, durability=50
    ),
    ItemType.COPPER_PICKAXE: ItemStats(
        weight=2.5, max_stack=1, category=ItemCategory.TOOL,
        damage=8.0, efficiency=2.5, durability=150
    ),
    ItemType.IRON_PICKAXE: ItemStats(
        weight=3.0, max_stack=1, category=ItemCategory.TOOL,
        damage=12.0, efficiency=4.0, durability=300
    ),
    
    # --- Weapons (Spears increase damage) ---
    ItemType.STONE_SPEAR: ItemStats(
        weight=1.5, max_stack=1, category=ItemCategory.WEAPON,
        damage=15.0, efficiency=1.0, durability=50
    ),
    ItemType.COPPER_SPEAR: ItemStats(
        weight=2.0, max_stack=1, category=ItemCategory.WEAPON,
        damage=25.0, efficiency=1.0, durability=150
    ),
    ItemType.IRON_SPEAR: ItemStats(
        weight=2.5, max_stack=1, category=ItemCategory.WEAPON,
        damage=40.0, efficiency=1.0, durability=300
    ),
    
    # --- Utilities ---
    ItemType.LEATHER_BAG: ItemStats(
        weight=0.5, max_stack=1, category=ItemCategory.ARMOR,
        carry_bonus=50.0 # +50 kg capacity
    ),
    ItemType.LEATHER_ARMOR: ItemStats(
        weight=1.0, max_stack=1, category=ItemCategory.ARMOR,
        defense=0.2 # 20% damage reduction
    ),
}
