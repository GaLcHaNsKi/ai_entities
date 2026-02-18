"""Ресурсы мира: растения, еда"""

import uuid
from core.physics import Vector2


class Plant:
    """
    Растение на карте
    - содержит энергию
    - время потребления (чтобы полностью съесть)
    - несколько существ могут есть одновременно
    """
    
    def __init__(self, x: float, y: float, energy: float = 100.0, consumption_time: float = 2.0):
        self.id = str(uuid.uuid4())
        self.pos = Vector2(x, y)
        self.energy = energy
        self.max_energy = energy
        self.consumption_time = consumption_time  # сек на полное поедание
        self.consumers = {}  # {entity_id: {'entity': entity_obj, 'eating_time': 0.0}}
        self.is_alive = True
    
    def add_consumer(self, entity_id: str, entity):
        """Добавить существо, которое ест это растение"""
        if entity_id not in self.consumers:
            self.consumers[entity_id] = {
                'entity': entity,
                'eating_time': 0.0
            }
    
    def remove_consumer(self, entity_id: str):
        """Удалить существо из едящих"""
        if entity_id in self.consumers:
            del self.consumers[entity_id]
    
    def update(self, dt: float) -> dict:
        """
        Обновление растения
        Распределяет энергию между едящими существами
        
        Возвращает словарь {entity_id: energy_gained}
        """
        if self.energy <= 0:
            self.is_alive = False
            return {}
        
        energy_given = {}
        
        if len(self.consumers) == 0:
            return energy_given
        
        # Расход энергии за dt: energy_per_tick = (energy / consumption_time) * dt
        num_consumers = len(self.consumers)
        energy_per_tick = (self.max_energy / self.consumption_time) * dt
        energy_per_consumer = energy_per_tick / num_consumers
        
        for entity_id, consumer_data in self.consumers.items():
            # Ограничиваем энергию, которую можно взять
            energy_to_give = min(energy_per_consumer, self.energy)
            
            self.energy -= energy_to_give
            consumer_data['eating_time'] += dt
            
            energy_given[entity_id] = energy_to_give
        
        return energy_given
    
    def get_eating_progress(self, entity_id: str) -> float:
        """Прогресс поедания в процентах (0-1)"""
        if entity_id not in self.consumers:
            return 0.0
        eating_time = self.consumers[entity_id]['eating_time']
        return min(1.0, eating_time / self.consumption_time)
    
    def __repr__(self):
        return f"Plant(pos={self.pos}, energy={self.energy:.1f}, consumers={len(self.consumers)})"


class ResourceNode:
    """
    Статический ресурс на карте.
    Типы: tree, stone, copper, iron.
    """

    def __init__(self, x: float, y: float, resource_type: str, amount: float = 100.0):
        self.id = str(uuid.uuid4())
        self.pos = Vector2(x, y)
        self.resource_type = resource_type
        
        # Общее количество доступного ресурса (float), но добывается кусками
        self.amount = amount 
        self.max_amount = amount
        self.is_alive = True
        
        self.miners = {} # {entity_id: {'tool_efficiency': 1.0, 'accumulated': 0.0}}
        self.yield_cost = 10.0 # Сколько 'усилий' нужно на 1 единицу ресурса

    def add_miner(self, entity_id: str, efficiency: float = 1.0):
        if entity_id not in self.miners:
            self.miners[entity_id] = {
                'tool_efficiency': efficiency,
                'accumulated': 0.0
            }
        else:
            self.miners[entity_id]['tool_efficiency'] = efficiency

    def remove_miner(self, entity_id: str):
        if entity_id in self.miners:
            del self.miners[entity_id]

    def update(self, dt: float) -> dict:
        """
        Возвращает {entity_id: int_items_gathered}
        """
        if self.amount <= 0:
            self.is_alive = False
            return {}
            
        items_given = {}
        empty_miners = []
        
        for entity_id, data in self.miners.items():
            # Mining power per second
            power = 5.0 * data['tool_efficiency'] # base speed * efficiency
            effort = power * dt
            
            # Check depletion
            if self.amount < (effort / self.yield_cost):
                effort = self.amount * self.yield_cost
            
            data['accumulated'] += effort
            self.amount -= (effort / self.yield_cost)
            
            if data['accumulated'] >= self.yield_cost:
                count = int(data['accumulated'] // self.yield_cost)
                data['accumulated'] -= (count * self.yield_cost)
                
                # Update gathered dict
                items_given[entity_id] = count
                
        if self.amount <= 0.1:
            self.is_alive = False
            
        return items_given

    def __repr__(self):
        return f"ResourceNode(type={self.resource_type}, pos={self.pos}, amount={self.amount:.1f})"
