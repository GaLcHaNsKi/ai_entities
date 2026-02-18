"""Конфигурация параметров мира и существ"""

from dataclasses import dataclass


@dataclass
class WorldConfig:
    """Конфигурация мира"""
    width: float = 1200.0
    height: float = 1200.0
    plant_count: int = 100
    plant_energy: float = 100.0
    plant_consumption_time: float = 2.5  # Увеличено: травоядные получают энергию дольше
    tree_count: int = 35
    stone_count: int = 28
    copper_count: int = 14
    iron_count: int = 8


@dataclass
class HerbivoreConfig:
    """Конфигурация травоядных"""
    count: int = 15
    max_energy: float = 130.0    # Увеличена макс энергия
    initial_energy: float = 110.0  # Увеличена начальная энергия (больше энергии для поиска еды)
    vision_range: float = 60.0
    max_speed: float = 80.0
    reproduction_energy_threshold: float = 90.0
    brain_type: str = "heuristic"  # "heuristic" | "rl"


@dataclass
class PredatorConfig:
    """Конфигурация хищников"""
    count: int = 4
    max_energy: float = 200.0     # Увеличена макс энергия
    initial_energy: float = 180.0  # Увеличена начальная энергия (хватит на поиск добычи)
    vision_range: float = 150.0  # дальше видят
    max_speed: float = 100.0
    attack_range: float = 12.0  # большая дистанция атаки
    attack_damage: float = 50.0  # увеличен базовый урон
    attack_cooldown: float = 0.35  # еще быстрее атакуют
    reproduction_energy_threshold: float = 120.0  # пороге для размножения
    brain_type: str = "heuristic"  # "heuristic" | "rl"


@dataclass
class SmartConfig:
    """Конфигурация разумных существ"""
    count: int = 6
    max_energy: float = 120.0
    initial_energy: float = 95.0
    vision_range: float = 95.0
    max_speed: float = 88.0
    attack_range: float = 10.0
    attack_damage: float = 18.0
    attack_cooldown: float = 0.45
    reproduction_energy_threshold: float = 85.0
    brain_type: str = "heuristic"


class SimulationConfig:
    """Главная конфигурация симуляции"""
    
    def __init__(self):
        self.world = WorldConfig()
        self.herbivores = HerbivoreConfig()
        self.predators = PredatorConfig()
        self.smarts = SmartConfig()
        
        # Параметры симуляции
        self.dt = 0.016  # 60 FPS
        self.max_frames = 1000
        self.update_interval = 30  # выводить статистику каждые N кадров


# Предустановки разных сценариев
class Presets:
    """Предустановленные конфигурации"""
    
    @staticmethod
    def balanced():
        """Сбалансированный мир"""
        config = SimulationConfig()
        config.world = WorldConfig(
            width=1400.0,
            height=1400.0,
            plant_count=100,
            plant_energy=100.0,
            plant_consumption_time=2.5,
            tree_count=35,
            stone_count=28,
            copper_count=14,
            iron_count=8,
        )
        config.herbivores = HerbivoreConfig(
            count=20,
            initial_energy=110.0
        )
        config.predators = PredatorConfig(
            count=5,
            initial_energy=180.0
        )
        config.smarts = SmartConfig(
            count=6,
            initial_energy=95.0
        )
        return config
    
    @staticmethod
    def herbivore_dominated():
        """Мир, где доминируют травоядные"""
        config = SimulationConfig()
        config.world = WorldConfig(
            width=1700.0,
            height=1700.0,
            plant_count=150,
            plant_energy=120.0,
            plant_consumption_time=2.5,
            tree_count=45,
            stone_count=30,
            copper_count=16,
            iron_count=9,
        )
        config.herbivores = HerbivoreConfig(
            count=30,
            initial_energy=120.0
        )
        config.predators = PredatorConfig(
            count=2,
            initial_energy=180.0,
            attack_damage=40.0
        )
        config.smarts = SmartConfig(
            count=8,
            initial_energy=100.0
        )
        return config
    
    @staticmethod
    def predator_dominant():
        """Мир, где доминируют хищники"""
        config = SimulationConfig()
        config.world = WorldConfig(
            width=1200.0,
            height=1200.0,
            plant_count=120,
            plant_energy=100.0,
            plant_consumption_time=2.5,
            tree_count=24,
            stone_count=22,
            copper_count=11,
            iron_count=6,
        )
        config.herbivores = HerbivoreConfig(
            count=18,
            initial_energy=75.0
        )
        config.predators = PredatorConfig(
            count=8,
            initial_energy=145.0
        )
        config.smarts = SmartConfig(
            count=5,
            initial_energy=90.0
        )
        return config
    
    @staticmethod
    def scarce_resources():
        """Мир с дефицитом ресурсов"""
        config = SimulationConfig()
        config.world = WorldConfig(
            width=2000.0,
            height=2000.0,
            plant_count=80,
            plant_energy=100.0,
            plant_consumption_time=2.5,
            tree_count=30,
            stone_count=26,
            copper_count=12,
            iron_count=7,
        )
        config.herbivores = HerbivoreConfig(
            count=12,
            initial_energy=65.0
        )
        config.predators = PredatorConfig(
            count=4,
            initial_energy=145.0
        )
        config.smarts = SmartConfig(
            count=4,
            initial_energy=85.0
        )
        return config
