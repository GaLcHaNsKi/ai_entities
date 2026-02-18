from typing import Dict, List, Optional
from core.items import ItemType, ITEM_DB, ItemCategory

class Recipe:
    def __init__(self, result: ItemType, amount: int, ingredients: Dict[ItemType, int], station_required: str = None):
        self.result = result
        self.amount = amount
        self.ingredients = ingredients
        self.station_required = station_required # e.g. "manual", "stump", "furnace"

# Define Recipes
RECIPES: List[Recipe] = [
    # Tools
    Recipe(ItemType.STONE_PICKAXE, 1, {ItemType.WOOD: 2, ItemType.STONE: 3}, "manual"),
    Recipe(ItemType.STONE_SPEAR, 1, {ItemType.WOOD: 3, ItemType.STONE: 1}, "manual"),
    
    # Advanced Tools (Copper)
    Recipe(ItemType.COPPER_INGOT, 1, {ItemType.COPPER_ORE: 1}, "furnace"), # Simplified smelting
    Recipe(ItemType.COPPER_PICKAXE, 1, {ItemType.WOOD: 2, ItemType.COPPER_INGOT: 3}, "workbench"),
    Recipe(ItemType.COPPER_SPEAR, 1, {ItemType.WOOD: 3, ItemType.COPPER_INGOT: 1}, "workbench"),
    
    # Advanced Tools (Iron)
    Recipe(ItemType.IRON_INGOT, 1, {ItemType.IRON_ORE: 1}, "furnace"),
    Recipe(ItemType.IRON_PICKAXE, 1, {ItemType.WOOD: 2, ItemType.IRON_INGOT: 3}, "workbench"),
    Recipe(ItemType.IRON_SPEAR, 1, {ItemType.WOOD: 3, ItemType.IRON_INGOT: 1}, "workbench"),
    
    # Utility
    Recipe(ItemType.LEATHER_BAG, 1, {ItemType.LEATHER: 5}, "manual"),
    Recipe(ItemType.LEATHER_ARMOR, 1, {ItemType.LEATHER: 8}, "manual"),
    
    # Cooking
    Recipe(ItemType.COOKED_MEAT, 1, {ItemType.MEAT: 1, ItemType.WOOD: 1}, "campfire"), # or manual for simplicity
]

class CraftingSystem:
    @staticmethod
    def get_available_recipes(inventory, nearby_stations: List[str] = None) -> List[Recipe]:
        """Returns list of recipes that can be crafted with current inventory and stations"""
        nearby_stations = nearby_stations or ["manual"]
        available = []
        
        for recipe in RECIPES:
            # Check station
            if recipe.station_required and recipe.station_required not in nearby_stations:
                # Basic logical fallback: "manual" recipes always available anywhere? 
                # Or "manual" implies no station.
                if recipe.station_required != "manual":
                    continue
            
            # Check ingredients
            can_craft = True
            for item, count in recipe.ingredients.items():
                if not inventory.has_item(item, count):
                    can_craft = False
                    break
            
            if can_craft:
                available.append(recipe)
                
        return available

    @staticmethod
    def craft(recipe: Recipe, inventory) -> bool:
        """Attempts to craft. Deducts ingredients, adds result. Checks weight limits."""
        # 1. Check ingredients again
        for item, count in recipe.ingredients.items():
            if not inventory.has_item(item, count):
                return False
                
        # 2. Check if result fits (Complex: we remove ingredients first, creating space, THEN add result)
        # But we must be careful not to delete items if we can't fit the result.
        
        current_weight = inventory.current_weight
        ingredients_weight = 0.0
        for item, count in recipe.ingredients.items():
             ingredients_weight += ITEM_DB[item].weight * count
             
        result_weight = ITEM_DB[recipe.result].weight * recipe.amount
        
        projected_weight = current_weight - ingredients_weight + result_weight
        
        if projected_weight > inventory.max_capacity:
            return False 
            
        # 3. Execute
        for item, count in recipe.ingredients.items():
            inventory.remove_item(item, count)
            
        inventory.add_item(recipe.result, recipe.amount)
        return True
