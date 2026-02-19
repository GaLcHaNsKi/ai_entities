"""Базовый класс для всех существ в мире"""

import uuid
from abc import ABC, abstractmethod
from core.physics import Vector2, EnergySystem


class Entity(ABC):
    """
    Базовый класс для всех существ
    Содержит позицию, скорость, энергию, здоровье
    """
    
    def __init__(self, x: float, y: float, entity_type: str = "entity"):
        self.id = str(uuid.uuid4())
        self.entity_type = entity_type
        
        # Физика
        self.pos = Vector2(x, y)
        self.velocity = Vector2(0, 0)  # вектор скорости
        self.max_speed = 100.0
        
        # Энергия
        self.energy = 50.0
        self.max_energy = 100.0
        
        # Здоровье (отдельное от энергии — для боевых повреждений)
        self.health = 100.0
        self.max_health = 100.0
        
        # Состояние
        self.is_alive = True
        self.age = 0.0  # время жизни в секундах
        
        # Размер для визуализации (радиус)
        self.radius = 5.0
        
        # Сенсоры (видимость)
        self.vision_range = 150.0  # насколько далеко видит
    
    def apply_force(self, force: Vector2):
        """Применить силу (изменить скорость)"""
        self.velocity = self.velocity + force
        # Ограничиваем скорость максимумом
        max_speed = EnergySystem.calculate_max_speed(self.energy, self.max_energy)
        self.velocity = self.velocity.clamp_magnitude(max_speed)
    
    def update(self, dt: float, world=None):
        """
        Обновление состояния существа каждый фрейм
        dt - время прошедшее с прошлого кадра (в секундах)
        world - ссылка на объект World (для сенсоров)
        """
        # Обновляем возраст
        self.age += dt
        
        # Движение
        self.pos = self.pos + self.velocity * dt
        
        # Расход энергии на движение
        movement_cost = EnergySystem.calculate_movement_cost(self.velocity.magnitude(), dt, self.entity_type)
        
        # Базовый расход энергии
        metabolic_cost = EnergySystem.calculate_metabolic_cost(dt)
        
        self.energy -= (movement_cost + metabolic_cost)
        
        # Проверяем смерть от голода
        if self.energy <= 0:
            self.is_alive = False
        
        # Ограничиваем энергию максимумом
        if self.energy > self.max_energy:
            self.energy = self.max_energy
    
    def gain_energy(self, amount: float):
        """Получить энергию"""
        self.energy = min(self.max_energy, self.energy + amount)
    
    def take_damage(self, amount: float):
        """Получить урон (потеря здоровья и энергии)"""
        self.health -= amount
        self.energy -= amount * 0.5  # Также немного энергии
        if self.health <= 0:
            self.is_alive = False
    
    @abstractmethod
    def behavior(self, dt: float, world=None):
        """
        Поведение существа - переопределяется в подклассах
        Здесь ИИ решает что делать
        """
        pass
    
    def get_sensor_data(self, world) -> dict:
        """
        Получить информацию об окружении для ИИ.
        OPTIMIZED: Использует spatial search (get_plants_in_radius, get_entities_in_radius)
        вместо O(N) полного перебора.
        
        Возвращает:
        {
            'self_energy': уровень энергии (0-1),
            'nearby_plants': список близких растений (отсортирован по расстоянию),
            'nearby_herbivores': список близких травоядных,
            'nearby_predators': список близких хищников,
            'nearby_smarts': список близких смарт существ,
        }
        """
        data = {
            'self_energy': self.energy / self.max_energy,
            'nearby_plants': [],
            'nearby_herbivores': [],
            'nearby_predators': [],
            'nearby_smarts': [],
            'world_width': world.width if world else 500,
            'world_height': world.height if world else 500,
        }
        
        if world is None:
            return data
        
        # OPTIMIZED: Используем spatial search вместо O(N) перебора
        # get_plants_in_radius уже отсортирован по расстоянию
        plants_nearby = world.get_plants_in_radius(self.pos, self.vision_range)
        for plant, dist in plants_nearby:
            if plant.is_alive:
                direction = (plant.pos - self.pos).normalize()
                data['nearby_plants'].append({
                    'distance': dist,
                    'direction': direction,
                    'energy': plant.energy,
                    'id': plant.id
                })
        
        # OPTIMIZED: Spatial search для сущностей
        entities_nearby = world.get_entities_in_radius(self.pos, self.vision_range, exclude_id=self.id)
        for entity, dist in entities_nearby:
            if not entity.is_alive:
                continue
            
            direction = (entity.pos - self.pos).normalize()
            entity_data = {
                'distance': dist,
                'direction': direction,
                'velocity': entity.velocity,
                'energy': entity.energy,
                'id': entity.id
            }
            
            if entity.entity_type == "herbivore":
                data['nearby_herbivores'].append(entity_data)
            elif entity.entity_type == "predator":
                data['nearby_predators'].append(entity_data)
            elif entity.entity_type == "smart":
                data['nearby_smarts'].append(entity_data)
        
        return data
    
    def __repr__(self):
        return f"{self.entity_type}(id={self.id[:8]}..., pos={self.pos}, energy={self.energy:.1f})"
