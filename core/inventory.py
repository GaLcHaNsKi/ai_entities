from typing import Dict, Optional, List
from core.items import ItemType, ITEM_DB, ItemCategory

class Inventory:
    def __init__(self, capacity: float = 30.0):
        self._items: Dict[ItemType, int] = {}  # type -> count
        self.base_capacity = capacity
        self.capacity_modifier = 0.0
        
    @property
    def max_capacity(self) -> float:
        return self.base_capacity + self.capacity_modifier
    
    @property
    def current_weight(self) -> float:
        total = 0.0
        for item_type, count in self._items.items():
            stats = ITEM_DB.get(item_type)
            if stats:
                total += stats.weight * count
        return total
    
    @property
    def is_full(self) -> bool:
        return self.current_weight >= self.max_capacity

    def can_add(self, item_type: ItemType, amount: int = 1) -> bool:
        stats = ITEM_DB.get(item_type)
        if not stats:
            return False
        added_weight = stats.weight * amount
        return (self.current_weight + added_weight) <= self.max_capacity

    def add_item(self, item_type: ItemType, amount: int = 1) -> int:
        """
        Adds item(s) to inventory. Returns amount actually added.
        """
        if amount <= 0:
            return 0
            
        stats = ITEM_DB.get(item_type)
        if not stats:
            return 0
            
        # Calculate how many we can fit
        remaining_capacity = self.max_capacity - self.current_weight
        max_fit = int(remaining_capacity / stats.weight)
        
        to_add = min(amount, max_fit)
        
        if to_add > 0:
            self._items[item_type] = self._items.get(item_type, 0) + to_add
            
        return to_add

    def remove_item(self, item_type: ItemType, amount: int = 1) -> bool:
        """
        Removes item(s). Returns True if successful.
        """
        if self._items.get(item_type, 0) >= amount:
            self._items[item_type] -= amount
            if self._items[item_type] <= 0:
                del self._items[item_type]
            return True
        return False
    
    def has_item(self, item_type: ItemType, amount: int = 1) -> bool:
        return self._items.get(item_type, 0) >= amount

    def get_count(self, item_type: ItemType) -> int:
        return self._items.get(item_type, 0)
        
    def get_contents(self) -> Dict[ItemType, int]:
        return self._items.copy()
    
    def clear(self):
        self._items.clear()
