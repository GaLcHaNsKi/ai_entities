"""Система ИИ и мозга для существ — базовый класс и эвристические мозги."""

import random
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import json

from core.physics import Vector2


class Brain(ABC):
    """Абстрактный класс для мозга существа"""
    
    @abstractmethod
    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        """
        Принять решение на основе сенсорных данных.
        
        Args:
            sensor_data: данные от сенсоров (из entity.get_sensor_data())
            entity:      ссылка на управляемое существо (для доступа к pos/energy/...)
        
        Returns:
            {
                'action': 'move' | 'attack' | 'eat' | 'flee' | 'idle',
                'target': Vector2 или None,
                'speed': float
            }
        """
        pass


# ---------------------------------------------------------------------------
#  Эвристические мозги (перенесены из hardcoded behavior в herbivore/predator)
# ---------------------------------------------------------------------------

class HeuristicHerbivoreBrain(Brain):
    """
    Эвристическое поведение травоядного:
    1. Бежать от хищников
    2. Искать и есть растения
    3. Случайное блуждание
    """
    
    def __init__(self):
        self.random_direction_timer = 0.0
        self._random_velocity = Vector2(0, 0)
    
    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        if entity is None:
            return {'action': 'idle', 'target': None, 'speed': 0}
        
        predators = sensor_data.get('nearby_predators', []) + sensor_data.get('nearby_smarts', [])
        plants = sensor_data.get('nearby_plants', [])
        
        # 1. Бегство от хищников
        if predators and entity.energy > 20:
            closest = min(predators, key=lambda p: p['distance'])
            flee_pos = entity.pos + closest['direction'] * 100
            flee_dir = (entity.pos - flee_pos).normalize()
            return {'action': 'flee', 'target': flee_dir, 'speed': 65}
        
        # 2. Поиск еды
        if plants:
            closest = min(plants, key=lambda p: p['distance'])
            if closest['distance'] < 12:
                return {
                    'action': 'eat',
                    'target': closest.get('direction', Vector2(0, 0)),
                    'speed': 0,
                    'plant_id': closest['id'],
                }
            else:
                target_dir = closest['direction']
                return {'action': 'move', 'target': target_dir, 'speed': 50}
        
        # 3. Случайное блуждание
        return {'action': 'wander', 'target': None, 'speed': 25}


class HeuristicPredatorBrain(Brain):
    """
    Эвристическое поведение хищника:
    1. Охота на травоядных
    2. Бегство от более сильных хищников
    3. Случайное блуждание
    """
    
    def __init__(self):
        self.random_direction_timer = 0.0
        self._random_velocity = Vector2(0, 0)
    
    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        if entity is None:
            return {'action': 'idle', 'target': None, 'speed': 0}
        
        herbivores = sensor_data.get('nearby_herbivores', [])
        smarts = sensor_data.get('nearby_smarts', [])
        preys = herbivores + smarts
        predators = sensor_data.get('nearby_predators', [])
        
        # 1. Охота на травоядных
        if preys:
            closest = min(preys, key=lambda h: h['distance'])
            if closest['distance'] < getattr(entity, 'attack_range', 12):
                return {
                    'action': 'attack',
                    'target': closest.get('direction', Vector2(0, 0)),
                    'speed': 0,
                    'prey_id': closest['id'],
                }
            else:
                target_dir = closest['direction']
                return {'action': 'move', 'target': target_dir, 'speed': 85}
        
        # 2. Бегство от более сильных хищников
        if predators:
            stronger = [p for p in predators if p['energy'] > entity.energy * 1.2]
            if stronger:
                closest = min(stronger, key=lambda p: p['distance'])
                flee_pos = entity.pos + closest['direction'] * 100
                flee_dir = (entity.pos - flee_pos).normalize()
                return {'action': 'flee', 'target': flee_dir, 'speed': 75}
        
        # 3. Случайное блуждание
        return {'action': 'wander', 'target': None, 'speed': 35}


class HeuristicSmartBrain(Brain):
    """
    Эвристическое поведение разумного существа:
    0. Избегать выхода за границы карты
    1. Убегать от близких хищников
    2. Охотиться на травоядных
    3. Есть растения как fallback
    4. Случайное блуждание
    """

    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        if entity is None:
            return {'action': 'idle', 'target': None, 'speed': 0}

        # 0. Избегание границ (Stay in bounds)
        world_w = sensor_data.get('world_width', 1200)
        world_h = sensor_data.get('world_height', 1200)
        margin = 50.0
        
        if (entity.pos.x < margin or entity.pos.x > world_w - margin or 
            entity.pos.y < margin or entity.pos.y > world_h - margin):
            
            # Вектор к центру карты
            center_dir = (Vector2(world_w/2, world_h/2) - entity.pos).normalize()
            return {'action': 'move', 'target': center_dir, 'speed': 50}

        predators = sensor_data.get('nearby_predators', [])
        herbivores = sensor_data.get('nearby_herbivores', [])
        plants = sensor_data.get('nearby_plants', [])

        if predators:
            closest_pred = min(predators, key=lambda p: p['distance'])
            if closest_pred['distance'] < 22 and entity.energy > 20:
                flee_pos = entity.pos + closest_pred['direction'] * 100
                flee_dir = (entity.pos - flee_pos).normalize()
                return {'action': 'flee', 'target': flee_dir, 'speed': 80}

        if herbivores:
            closest_prey = min(herbivores, key=lambda h: h['distance'])
            if closest_prey['distance'] < getattr(entity, 'attack_range', 10):
                return {
                    'action': 'attack',
                    'target': closest_prey.get('direction', Vector2(0, 0)),
                    'speed': 0,
                    'prey_id': closest_prey['id'],
                }
            return {'action': 'move', 'target': closest_prey['direction'], 'speed': 78}

        if plants:
            closest_plant = min(plants, key=lambda p: p['distance'])
            if closest_plant['distance'] < 12:
                return {
                    'action': 'eat',
                    'target': closest_plant.get('direction', Vector2(0, 0)),
                    'speed': 0,
                    'plant_id': closest_plant['id'],
                }
            return {'action': 'move', 'target': closest_plant['direction'], 'speed': 55}

        return {'action': 'wander', 'target': None, 'speed': 30}


class SimpleBrain(Brain):
    """Заглушка — idle."""
    
    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        return {'action': 'idle', 'target': None, 'speed': 0}


# ---------------------------------------------------------------------------
#  Нейросетевой мозг (pure-Python, для эволюционного подхода)
# ---------------------------------------------------------------------------

class NeuralNetworkBrain(Brain):
    """
    Нейросеть для управления существом (чистый Python, без PyTorch).
    """
    
    def __init__(self, input_size: int, hidden_sizes: List[int], output_size: int):
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.output_size = output_size
        
        self.weights = []
        self.biases = []
        
        layer_sizes = [input_size] + hidden_sizes + [output_size]
        
        for i in range(len(layer_sizes) - 1):
            w = [[random.gauss(0, 1) for _ in range(layer_sizes[i])] 
                 for _ in range(layer_sizes[i + 1])]
            b = [random.gauss(0, 1) for _ in range(layer_sizes[i + 1])]
            
            self.weights.append(w)
            self.biases.append(b)
    
    def forward(self, inputs: List[float]) -> List[float]:
        activation = inputs
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            z = self._matrix_multiply(w, activation)
            z = [z[j] + b[j] for j in range(len(z))]
            if i < len(self.weights) - 1:
                activation = [max(0, x) for x in z]
            else:
                activation = [math.tanh(x) for x in z]
        return activation
    
    def _matrix_multiply(self, weights: List[List[float]], inputs: List[float]) -> List[float]:
        output = []
        for row in weights:
            result = sum(w * inp for w, inp in zip(row, inputs))
            output.append(result)
        return output
    
    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        return {'action': 'idle', 'target': None, 'speed': 0}
    
    def get_weights_dict(self) -> dict:
        return {
            'input_size': self.input_size,
            'hidden_sizes': self.hidden_sizes,
            'output_size': self.output_size,
            'weights': self.weights,
            'biases': self.biases
        }
    
    @staticmethod
    def from_weights(weights_dict: dict) -> 'NeuralNetworkBrain':
        brain = NeuralNetworkBrain(
            weights_dict['input_size'],
            weights_dict['hidden_sizes'],
            weights_dict['output_size']
        )
        brain.weights = weights_dict['weights']
        brain.biases = weights_dict['biases']
        return brain
    
    def mutate(self, mutation_rate: float = 0.1, mutation_strength: float = 0.5):
        for layer_weights in self.weights:
            for row in layer_weights:
                for i in range(len(row)):
                    if random.random() < mutation_rate:
                        row[i] += random.gauss(0, mutation_strength)
        for layer_biases in self.biases:
            for i in range(len(layer_biases)):
                if random.random() < mutation_rate:
                    layer_biases[i] += random.gauss(0, mutation_strength)


class GenomeEncoder:
    """Кодирование/декодирование генома."""
    
    @staticmethod
    def encode_genome(brain: NeuralNetworkBrain) -> str:
        return json.dumps(brain.get_weights_dict())
    
    @staticmethod
    def decode_genome(genome_str: str) -> NeuralNetworkBrain:
        return NeuralNetworkBrain.from_weights(json.loads(genome_str))


# ---------------------------------------------------------------------------
#  Фабрика мозгов
# ---------------------------------------------------------------------------

# Кэш загруженных RL-моделей (одна загрузка на тип существа)
_rl_brain_cache: dict = {}


def create_brain(brain_type: str, creature_type: str, model_path: str = None) -> Brain:
    """
    Фабрика: создать мозг нужного типа.
    
    Args:
        brain_type:    "heuristic" | "rl"
        creature_type: "herbivore" | "predator"
        model_path:    путь к модели (для RL)
    """
    if brain_type == "heuristic":
        if creature_type == "herbivore":
            return HeuristicHerbivoreBrain()
        elif creature_type == "smart":
            return HeuristicSmartBrain()
        else:
            return HeuristicPredatorBrain()
    
    elif brain_type == "rl":
        from ai.rl_brain import RLHerbivoreBrain, RLPredatorBrain, _SharedRLBrain
        
        cache_key = (creature_type, model_path)
        if cache_key not in _rl_brain_cache:
            # Загружаем модель один раз
            if creature_type == "herbivore":
                _rl_brain_cache[cache_key] = RLHerbivoreBrain(model_path=model_path)
            elif creature_type == "smart":
                _rl_brain_cache[cache_key] = RLHerbivoreBrain(model_path=model_path)
            else:
                _rl_brain_cache[cache_key] = RLPredatorBrain(model_path=model_path)
            print(f"[create_brain] Loaded RL model for {creature_type}")
        
        # Возвращаем лёгкую обёртку, шарящую одну модель
        return _SharedRLBrain(_rl_brain_cache[cache_key], agent_type=creature_type)
    
    else:
        return SimpleBrain()
