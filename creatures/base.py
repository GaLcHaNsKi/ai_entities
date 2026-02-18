"""Базовый класс для животных"""

from abc import ABC
from core.entity import Entity
from core.physics import Vector2


class Animal(Entity, ABC):
    """
    Базовый класс для всех животных (травоядные, хищники и т.д.)
    """
    
    def __init__(self, x: float, y: float, entity_type: str = "animal"):
        super().__init__(x, y, entity_type)
        
        # Поведение
        self.current_target_plant = None
        self.current_target_prey = None
        
        # Параметры размножения
        self.reproduction_energy_threshold = 70.0  # минимум энергии для размножения
        self.reproduction_cooldown = 0.0
    
    def move_towards(self, target_pos: Vector2, speed: float = 50.0):
        """Движение в направлении цели"""
        direction = (target_pos - self.pos).normalize()
        self.velocity = direction * speed
    
    def stop(self):
        """Остановиться"""
        self.velocity = Vector2(0, 0)
    
    def flee_from(self, danger_pos: Vector2, speed: float = 80.0):
        """Убегать от опасности"""
        direction = (self.pos - danger_pos).normalize()
        self.velocity = direction * speed
    
    def eat_plant(self, plant, dt: float):
        """
        Начать есть растение
        """
        plant.add_consumer(self.id, self)
    
    def stop_eating_plant(self, plant):
        """Перестать есть растение"""
        plant.remove_consumer(self.id)
    
    def can_reproduce(self) -> bool:
        """Может ли размножаться"""
        return self.energy >= self.reproduction_energy_threshold and self.reproduction_cooldown <= 0
    
    def reproduce(self):
        """
        Размножение - теряет энергию, создает потомка
        Возвращает новое существо (или None)
        """
        if not self.can_reproduce():
            return None
        
        # Теряем энергию
        reproduction_cost = self.max_energy * 0.4
        self.energy -= reproduction_cost
        self.reproduction_cooldown = 5.0  # секунд cooldown
        
        # Создаем потомка (копию)
        offspring = self.__class__(self.pos.x, self.pos.y)
        offspring.energy = reproduction_cost * 0.8
        
        return offspring
    
    def update(self, dt: float, world=None):
        """Обновление существа"""
        super().update(dt, world)
        
        # Обновляем cooldown размножения
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= dt
