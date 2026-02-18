"""Физика мира: вектора, движение, энергетика"""

import math


class Vector2:
    """2D вектор с базовыми операциями"""
    
    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)
    
    def __add__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x + other.x, self.y + other.y)
        return Vector2(self.x + other, self.y + other)
    
    def __sub__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x - other.x, self.y - other.y)
        return Vector2(self.x - other, self.y - other)
    
    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar):
        if scalar == 0:
            return Vector2(0, 0)
        return Vector2(self.x / scalar, self.y / scalar)
    
    def dot(self, other):
        """Скалярное произведение"""
        return self.x * other.x + self.y * other.y
    
    def magnitude(self):
        """Длина вектора"""
        return math.sqrt(self.x ** 2 + self.y ** 2)
    
    def magnitude_squared(self):
        """Квадрат длины (без sqrt, быстрее)"""
        return self.x ** 2 + self.y ** 2
    
    def normalize(self):
        """Нормализованный вектор (направление, длина = 1)"""
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)
    
    def distance_to(self, other):
        """Расстояние до другой точки"""
        return (self - other).magnitude()
    
    def distance_squared_to(self, other):
        """Квадрат расстояния (быстрее)"""
        return (self - other).magnitude_squared()
    
    def clamp_magnitude(self, max_mag):
        """Ограничить длину вектора"""
        mag = self.magnitude()
        if mag > max_mag:
            return self.normalize() * max_mag
        return Vector2(self.x, self.y)
    
    def __repr__(self):
        return f"Vector2({self.x:.2f}, {self.y:.2f})"
    
    def copy(self):
        return Vector2(self.x, self.y)


class EnergySystem:
    """Система энергии для существ"""
    
    # Константы
    MOVEMENT_COST_HERBIVORE = 0.0003  # травоядные тратят меньше энергии (было 0.015)
    MOVEMENT_COST_PREDATOR = 0.001   # хищники тратят немного больше (было 0.003)
    MOVEMENT_COST_SMART = 0.0002     # разумные экономнее двигаются (племенной стиль)
    MIN_SPEED_FOR_LIFE = 0.1
    METABOLIC_RATE = 0.000005  # базовый расход энергии (за просто существование)
    
    @staticmethod
    def calculate_movement_cost(speed_magnitude: float, dt: float, entity_type: str = "herbivore") -> float:
        """
        Расход энергии на движение
        Зависит от типа существа (травоядное или хищник)
        cost = speed² * coefficient * dt
        """
        if entity_type == "herbivore":
            coefficient = EnergySystem.MOVEMENT_COST_HERBIVORE
        elif entity_type == "smart":
            coefficient = EnergySystem.MOVEMENT_COST_SMART
        else:
            coefficient = EnergySystem.MOVEMENT_COST_PREDATOR
        cost = (speed_magnitude ** 2) * coefficient * dt
        return cost
    
    @staticmethod
    def calculate_metabolic_cost(dt: float) -> float:
        """Базовый расход энергии (дыхание, тепло и т.д.)"""
        return EnergySystem.METABOLIC_RATE * dt
    
    @staticmethod
    def calculate_max_speed(current_energy: float, max_energy: float = 100) -> float:
        """
        Максимальная скорость зависит от энергии
        При низкой энергии существо замедляется
        """
        energy_ratio = current_energy / max_energy if max_energy > 0 else 0
        # Базовая макс скорость 100, зависит от соотношения энергии
        base_max_speed = 100
        return base_max_speed * math.sqrt(energy_ratio)
