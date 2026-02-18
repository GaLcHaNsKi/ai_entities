"""Gymnasium Environment — обёртка над World для обучения RL-агентов."""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
import random

from core.world import World
from core.config import SimulationConfig, Presets
from core.physics import EnergySystem
from creatures.herbivore import Herbivore
from creatures.predator import Predator
from creatures.smart import SmartCreature
from core.items import ItemType
from core.building import BuildingType, BUILDING_DB
from ai.reward import RewardCalculator


# Максимальное число «слотов» ближайших объектов, попадающих в observation
MAX_NEARBY_PLANTS = 5
MAX_NEARBY_HERBIVORES = 3
MAX_NEARBY_PREDATORS = 3
MAX_NEARBY_RESOURCES = 5 # Деревья, камни и т.д.
MAX_NEARBY_BUILDINGS = 3 # Дома, фермы


def _encode_nearby(objects: list, max_n: int) -> np.ndarray:
    """
    Кодировать ближайшие объекты в фиксированный вектор.
    Каждый объект → (distance_norm, direction_x, direction_y, energy_norm).
    Недостающие слоты заполняются нулями.
    """
    result = np.zeros(max_n * 4, dtype=np.float32)
    sorted_objects = sorted(objects, key=lambda o: o['distance'])[:max_n]
    for i, obj in enumerate(sorted_objects):
        base = i * 4
        # Нормализуем расстояние (0..1 в радиусе видимости)
        result[base + 0] = min(obj['distance'] / 200.0, 1.0)
        result[base + 1] = obj['direction'].x
        result[base + 2] = obj['direction'].y
        result[base + 3] = min(obj.get('energy', 50) / 200.0, 1.0)
    return result


def _encode_nearby_entities(objects: list, max_n: int) -> np.ndarray:
    """
    Кодировать ближайшие динамические сущности (с вектором скорости).
    Каждый объект → (distance_norm, direction_x, direction_y, energy_norm, vel_x, vel_y).
    """
    result = np.zeros(max_n * 6, dtype=np.float32)
    sorted_objects = sorted(objects, key=lambda o: o['distance'])[:max_n]
    for i, obj in enumerate(sorted_objects):
        base = i * 6
        result[base + 0] = min(obj['distance'] / 200.0, 1.0)
        result[base + 1] = obj['direction'].x
        result[base + 2] = obj['direction'].y
        result[base + 3] = min(obj.get('energy', 50) / 200.0, 1.0)
        
        vel = obj.get('velocity')
        if vel:
            # Нормализуем скорость (примерно делим на 100)
            result[base + 4] = np.clip(vel.x / 100.0, -1.0, 1.0)
            result[base + 5] = np.clip(vel.y / 100.0, -1.0, 1.0)
        else:
            result[base + 4] = 0.0
            result[base + 5] = 0.0
    return result

def _encode_nearby_resources(objects: list, max_n: int) -> np.ndarray:
    """
    Кодирование ресурсов: [dist, dir_x, dir_y, type_code]
    type_code: 0=Tree, 0.33=Stone, 0.66=Copper, 1.0=Iron
    """
    result = np.zeros(max_n * 4, dtype=np.float32)
    sorted_objects = sorted(objects, key=lambda o: o['distance'])[:max_n]
    
    type_map = {
        "tree": 0.0,
        "stone": 0.33,
        "copper": 0.66,
        "iron": 1.0
    }
    
    for i, obj in enumerate(sorted_objects):
        base = i * 4
        result[base + 0] = min(obj['distance'] / 200.0, 1.0)
        result[base + 1] = obj['direction'].x
        result[base + 2] = obj['direction'].y
        
        t_code = type_map.get(obj.get('resource_type', ''), -1.0)
        result[base + 3] = t_code 
        
    return result


def _encode_nearby_buildings(buildings: list, max_n: int, owner_id: int) -> np.ndarray:
    """
    Encode buildings: (dist, dx, dy, type, is_mine, health)
    """
    result = np.zeros(max_n * 6, dtype=np.float32)
    sorted_b = sorted(buildings, key=lambda b: b['distance'])[:max_n]
    
    type_map = {
        BuildingType.HOUSE: 0.1,
        BuildingType.FARM_PLOT: 0.5,
        BuildingType.CAMPFIRE: 0.9,
    }
    
    for i, b in enumerate(sorted_b):
        base = i * 6
        result[base + 0] = min(b['distance'] / 200.0, 1.0)
        result[base + 1] = b['direction'].x
        result[base + 2] = b['direction'].y
        result[base + 3] = type_map.get(b['type'], 0.0)
        result[base + 4] = 1.0 if b['owner_id'] == owner_id else 0.0
        result[base + 5] = b['health_ratio']
    return result


class SingleAgentEnv(gym.Env):
    """
    Gymnasium-среда для обучения **одного** RL-агента.
    
    Параметры:
        agent_type: "herbivore", "predator", или "smart"
        ...
    """
    
    metadata = {"render_modes": ["human"], "render_fps": 30}
    
    def __init__(self, agent_type: str = "herbivore",
                 config: SimulationConfig = None,
                 max_steps: int = 4000,
                 opponent_model_path: str = None,
                 opponent_ratio: float = 0.5):
        super().__init__()
        
        self.agent_type = agent_type
        self.config = config or Presets.balanced()
        self.max_steps = max_steps
        self.current_step = 0
        self.opponent_model_path = opponent_model_path
        self.opponent_ratio = opponent_ratio
        
        # --- Observation space ---
        self_dim = 5
        plants_dim = MAX_NEARBY_PLANTS * 4
        herbs_dim = MAX_NEARBY_HERBIVORES * 6
        preds_dim = MAX_NEARBY_PREDATORS * 6
        
        if self.agent_type == "smart":
            # Extra channels for Smart Agent
            # Inventory (8 items: Wood, Stone, CopperOre, IronOre, Meat, Leather, CopperIngot, IronIngot)
            # Equipped (3 slots: Weapon, Tool, Armor - encoded as simple levels 0..1)
            # Nearby Resources (MAX_NEARBY_RESOURCES * 4)
            # Nearby Buildings (MAX_NEARBY_BUILDINGS * 6)
            inv_dim = 8
            equip_dim = 3
            res_dim = MAX_NEARBY_RESOURCES * 4
            bld_dim = MAX_NEARBY_BUILDINGS * 6
            self.obs_dim = self_dim + plants_dim + herbs_dim + preds_dim + inv_dim + equip_dim + res_dim + bld_dim
            
            # Action space expanded: [move_x, move_y, speed, mode, parameter]
            self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(5,), dtype=np.float32)
        else:
            self.obs_dim = self_dim + plants_dim + herbs_dim + preds_dim
            self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self.obs_dim,), dtype=np.float32
        )
        
        # Внутренние переменные
        self.world = None
        self.agent = None    # Ссылка на управляемое RL-агентом существо
        self.prev_energy = 0.0
        self.prev_closest_resource_dist = -1.0
        self._herb_memory_until_age = 0.0
        self._herb_memory_mode = None
        self._herb_memory_direction = None
        self._herb_memory_speed_factor = 0.0
    
    def reset(self, seed=None, options=None):
        """Сбросить среду и начать новый эпизод."""
        super().reset(seed=seed)
        self.current_step = 0
        
        # Создаём мир
        cfg = self.config
        
        # Override map size for smart training if not specified otherwise
        world_w = cfg.world.width
        world_h = cfg.world.height
        if self.agent_type == "smart":
             world_w = max(world_w, 1500)
             world_h = max(world_h, 1500)
             
        self.world = World(world_w, world_h)
        
        scale_factor = 2.0 if self.agent_type == "smart" else 1.0

        # Растения
        self.world.spawn_plants(
            count=int(cfg.world.plant_count * scale_factor),
            energy=cfg.world.plant_energy,
            consumption_time=cfg.world.plant_consumption_time,
        )

        # Статические ресурсы (пока не участвуют в reward напрямую,
        # но поддерживают одинаковую геометрию мира с main-simulation)
        self.world.spawn_resources(
            tree_count=int(getattr(cfg.world, 'tree_count', 0) * scale_factor),
            stone_count=int(getattr(cfg.world, 'stone_count', 0) * scale_factor),
            copper_count=int(getattr(cfg.world, 'copper_count', 0) * scale_factor),
            iron_count=int(getattr(cfg.world, 'iron_count', 0) * scale_factor),
        )
        
        # --- Загружаем RL-модель для оппонентов (если указана) ---
        opponent_brain_cls = None
        if self.opponent_model_path:
            from ai.rl_brain import RLBrain
            # Загружаем модель один раз, потом шарим между оппонентами
            if not hasattr(self, '_shared_opponent_model') or self._shared_opponent_model is None:
                # Use standard initialization instead of __new__ to ensure all attributes are set
                brain = RLBrain(
                    model_path=self.opponent_model_path,
                    agent_type="herbivore" if self.agent_type == "predator" else "predator"
                )
                self._shared_opponent_model = brain
            opponent_brain_cls = self._shared_opponent_model
        
        # --- Определяем, какой тип оппонента получает RL-мозг ---
        # Если обучаем predator, оппоненты-травоядные могут быть RL
        # Если обучаем herbivore, оппоненты-хищники могут быть RL
        opponent_type = "herbivore" if self.agent_type == "predator" else "predator"
        
        # Генерируем хищников
        # Увеличим количество животных если агент smart, чтобы среда была насыщеннее
        scale_factor = 2.0 if self.agent_type == "smart" else 1.0
        
        # Подправим размеры мира если smart (чтобы было где разгуляться)
        if self.agent_type == "smart":
             # Hardcode override: make world slightly larger for smart training
             # Or rely on Config passed in __init__. Let's respect config but maybe scale counts.
             pass

        # Генерируем травоядных
        h_count = int(cfg.herbivores.count * scale_factor)
        for i in range(h_count):
            use_rl = (
                opponent_brain_cls is not None
                and opponent_type == "herbivore"
                and i < int(h_count * self.opponent_ratio)
            )
            brain = None
            if use_rl:
                from ai.rl_brain import _SharedRLBrain
                brain = _SharedRLBrain(opponent_brain_cls, agent_type="herbivore")
            h = Herbivore(
                x=random.uniform(0, cfg.world.width),
                y=random.uniform(0, cfg.world.height),
                brain=brain,
            )
            h.energy = cfg.herbivores.initial_energy
            h.max_energy = cfg.herbivores.max_energy
            h.health = 100.0
            h.max_health = 100.0
            h.vision_range = cfg.herbivores.vision_range
            h.max_speed = cfg.herbivores.max_speed
            h.reproduction_energy_threshold = cfg.herbivores.reproduction_energy_threshold
            self.world.add_entity(h)
        
        # Генерируем хищников
        p_count = int(cfg.predators.count * scale_factor)
        for i in range(p_count):
            use_rl = (
                opponent_brain_cls is not None
                and opponent_type == "predator"
                and i < int(p_count * self.opponent_ratio)
            )
            brain = None
            if use_rl:
                from ai.rl_brain import _SharedRLBrain
                brain = _SharedRLBrain(opponent_brain_cls, agent_type="predator")
            p = Predator(
                x=random.uniform(0, cfg.world.width),
                y=random.uniform(0, cfg.world.height),
                brain=brain,
            )
            p.energy = cfg.predators.initial_energy
            p.max_energy = cfg.predators.max_energy
            p.health = 120.0
            p.max_health = 120.0
            p.vision_range = cfg.predators.vision_range
            p.max_speed = cfg.predators.max_speed
            p.attack_range = cfg.predators.attack_range
            p.attack_damage = cfg.predators.attack_damage
            p.attack_cooldown = cfg.predators.attack_cooldown
            p.reproduction_energy_threshold = cfg.predators.reproduction_energy_threshold
            self.world.add_entity(p)

        # Если мы тренируем Smart, добавим еще несколько Smart-агентов (эвристических),
        # чтобы они могли создавать племя или конкурировать
        if self.agent_type == "smart":
            # Add 2-3 extra heuristic smart agents
            for _ in range(3):
                s = SmartCreature(
                    x=random.uniform(0, cfg.world.width),
                    y=random.uniform(0, cfg.world.height),
                    # No brain arg = default heuristic behavior (which we restored in smart.py)
                )
                s.health = 100.0
                s.max_health = 100.0
                self.world.add_entity(s)
        
        # Добавляем RL-агента
        if self.agent_type == "herbivore":
            self.agent = Herbivore(
                x=random.uniform(0, cfg.world.width),
                y=random.uniform(0, cfg.world.height),
            )
            self.agent.energy = cfg.herbivores.initial_energy
            self.agent.max_energy = cfg.herbivores.max_energy
            self.agent.health = 100.0
            self.agent.max_health = 100.0
            self.agent.vision_range = cfg.herbivores.vision_range
            self.agent.max_speed = cfg.herbivores.max_speed
            self.agent.reproduction_energy_threshold = cfg.herbivores.reproduction_energy_threshold
        elif self.agent_type == "smart":
            self.agent = SmartCreature(
                 x=random.uniform(0, cfg.world.width),
                 y=random.uniform(0, cfg.world.height),
            )
            # Smart defaults (using overrides from config if available in future, for now hardcoded in class or here)
            self.agent.vision_range = 95.0
            self.agent.max_speed = 88.0
            self.agent.health = 100.0
            self.agent.max_health = 100.0
        else:
            self.agent = Predator(
                x=random.uniform(0, cfg.world.width),
                y=random.uniform(0, cfg.world.height),
            )
            self.agent.energy = cfg.predators.initial_energy
            self.agent.max_energy = cfg.predators.max_energy
            self.agent.health = 120.0
            self.agent.max_health = 120.0
            self.agent.vision_range = cfg.predators.vision_range
            self.agent.max_speed = cfg.predators.max_speed
            self.agent.attack_range = cfg.predators.attack_range
            self.agent.attack_damage = cfg.predators.attack_damage
            self.agent.attack_cooldown = cfg.predators.attack_cooldown
            self.agent.reproduction_energy_threshold = cfg.predators.reproduction_energy_threshold
        
        # Помечаем агента — поведение будет переопределено через step()
        self.agent._is_rl_agent = True
        self.world.add_entity(self.agent)
        
        self.prev_energy = self.agent.energy
        self.prev_closest_prey_dist = -1.0
        self.prev_closest_plant_dist = -1.0
        self.prev_closest_predator_dist = -1.0
        self.prev_closest_resource_dist = -1.0
        self.prev_pos = self.agent.pos
        self.prev_velocity = self.agent.velocity
        self._herb_memory_until_age = 0.0
        self._herb_memory_mode = None
        self._herb_memory_direction = None
        self._herb_memory_speed_factor = 0.0
        
        obs = self._get_obs()
        info = {}
        return obs, info
    
    def step(self, action: np.ndarray):
        """Один шаг среды."""
        self.current_step += 1

        prev_pos = self.agent.pos
        prev_velocity = self.agent.velocity
        
        # --- Применяем action к RL-агенту ---
        move_x = float(np.clip(action[0], -1.0, 1.0))
        move_y = float(np.clip(action[1], -1.0, 1.0))
        
        # Хищник: [-1,1] → [0.3, 1.0] — всегда двигается
        # Травоядное: [-1,1] → [0.2, 1.0] — чтобы не залипал на месте
        if self.agent_type == "predator":
            speed_factor = 0.3 + 0.7 * (float(np.clip(action[2], -1.0, 1.0)) + 1.0) / 2.0
        else:
            speed_factor = 0.2 + 0.8 * (float(np.clip(action[2], -1.0, 1.0)) + 1.0) / 2.0
        
        from core.physics import Vector2
        direction = Vector2(move_x, move_y)
        direction_mag = direction.magnitude()
        herb_sensors = None
        threats = []
        plants = []
        closest_threat = None
        closest_food = None
        used_memory = False

        if self.agent_type == "herbivore":
            herb_sensors = self.agent.get_sensor_data(self.world)
            threats = herb_sensors.get('nearby_predators', []) + herb_sensors.get('nearby_smarts', [])
            plants = herb_sensors.get('nearby_plants', [])
            closest_threat = min(threats, key=lambda p: p['distance']) if threats else None
            closest_food = min(plants, key=lambda p: p['distance']) if plants else None

            panic_enter = getattr(self.agent, 'panic_enter_distance', 34.0)
            immediate_threat = closest_threat is not None and closest_threat['distance'] <= panic_enter

            if immediate_threat:
                self._herb_memory_until_age = 0.0
                self._herb_memory_mode = None
            elif self.agent.age < self._herb_memory_until_age:
                if self._herb_memory_mode == "eat" and closest_food is not None and closest_food['distance'] <= 14.0:
                    direction = Vector2(0, 0)
                    speed_factor = 0.0
                    used_memory = True
                elif self._herb_memory_mode == "move" and self._herb_memory_direction is not None:
                    direction = Vector2(self._herb_memory_direction.x, self._herb_memory_direction.y)
                    speed_factor = self._herb_memory_speed_factor
                    used_memory = True
                else:
                    self._herb_memory_until_age = 0.0
                    self._herb_memory_mode = None

        if not used_memory:
            # Dead-zone: tiny vectors from policy create jitter/spin when normalized.
            # For herbivores, switch to purposeful fallback instead of random heading.
            if direction_mag > 0.18:
                direction = direction.normalize()
            elif self.agent_type == "herbivore":
                if threats and self.agent.energy > 15:
                    direction = Vector2(-closest_threat['direction'].x, -closest_threat['direction'].y).normalize()
                elif closest_food is not None and closest_food['distance'] <= 12.0:
                    # Близко к еде: останавливаемся и удерживаем eat короткой памятью.
                    direction = Vector2(0, 0)
                    speed_factor = 0.0
                elif plants:
                    food_dir = closest_food['direction']
                    direction = food_dir.normalize() if food_dir.magnitude() > 0 else Vector2(0, 0)
                elif prev_velocity.magnitude() > 0.2:
                    direction = prev_velocity.normalize()
                else:
                    direction = Vector2(0, 0)
            else:
                direction = Vector2(0, 0)

        # Smooth abrupt heading flips for herbivores (reduces spinning exploit)
        if self.agent_type == "herbivore" and direction.magnitude() > 0 and prev_velocity.magnitude() > 0:
            prev_dir = prev_velocity.normalize()
            direction = (prev_dir * 0.65 + direction * 0.35)
            if direction.magnitude() > 0:
                direction = direction.normalize()

        if self.agent_type == "herbivore":
            panic_enter = getattr(self.agent, 'panic_enter_distance', 34.0)
            immediate_threat = closest_threat is not None and closest_threat['distance'] <= panic_enter

            if immediate_threat:
                self._herb_memory_until_age = 0.0
                self._herb_memory_mode = None
            elif direction.magnitude() == 0 and closest_food is not None and closest_food['distance'] <= 12.0:
                self._herb_memory_until_age = self.agent.age + random.uniform(0.14, 0.26)
                self._herb_memory_mode = "eat"
                self._herb_memory_direction = None
                self._herb_memory_speed_factor = 0.0
            elif direction.magnitude() > 0:
                self._herb_memory_until_age = self.agent.age + random.uniform(0.10, 0.30)
                self._herb_memory_mode = "move"
                self._herb_memory_direction = Vector2(direction.x, direction.y)
                self._herb_memory_speed_factor = speed_factor

        self.agent.velocity = direction * (self.agent.max_speed * speed_factor)
        
        # --- Специальные действия для Smart ---
        craft_success = False
        build_success = False
        equip_success = False
        gather_contact = False
        gather_items_gained = 0
        crafted_tier = 0
        smart_mode = None
        inv_before = None
        
        if self.agent_type == "smart" and hasattr(self.agent, 'inventory'):
            inv_before = self.agent.inventory.get_contents()

        def _item_tier(item_type) -> int:
            name = item_type.value if hasattr(item_type, 'value') else str(item_type)
            if "iron" in name:
                return 3
            if "copper" in name:
                return 2
            return 1

        if self.agent_type == "smart" and action.shape[0] >= 5:
            mode = action[3]
            param = action[4] # -1..1 maps to index
            
            # Mode processing
            if mode >= 0.2 and mode < 0.5: # Gather
                smart_mode = "gather"
                # Param maps to resource index 0..MAX-1
                res_idx = int((param + 1.0) / 2.0 * MAX_NEARBY_RESOURCES)
                res_idx = min(res_idx, MAX_NEARBY_RESOURCES - 1)
                
                # Optimized search: finding Nth closest resource without full sort
                # Only check resources within vision + margin
                search_radius_sq = (self.agent.vision_range + 50.0)**2
                candidates = []
                for r in self.world.resources:
                    if not r.is_alive: continue
                    dist_sq = (r.pos.x - self.agent.pos.x)**2 + (r.pos.y - self.agent.pos.y)**2
                    if dist_sq < search_radius_sq:
                        candidates.append((dist_sq, r))
                
                # Sort only candidates (much smaller list)
                candidates.sort(key=lambda x: x[0])
                
                if res_idx < len(candidates):
                    target_res = candidates[res_idx][1]
                    gather_contact = self.agent.gather_resource(target_res, self.config.dt)
                    
            elif mode >= 0.5 and mode < 0.8: # Craft / Equip
                smart_mode = "craft"
                from core.crafting import RECIPES
                # Param maps to Recipe index
                # 9 receipts currently
                recipe_idx = int((param + 1.0) / 2.0 * len(RECIPES))
                recipe_idx = min(recipe_idx, len(RECIPES) - 1)
                target_recipe = RECIPES[recipe_idx]
                
                # Try to craft
                if self.agent.try_craft(target_recipe.result):
                    craft_success = True
                    crafted_tier = _item_tier(target_recipe.result)
                    # Auto-equip if tool/weapon
                    equip_success = self.agent.try_equip(target_recipe.result)

            elif mode >= 0.8: # Build
                smart_mode = "build"
                b_types = [BuildingType.HOUSE, BuildingType.FARM_PLOT, BuildingType.CAMPFIRE]
                b_idx = int((param + 1.0) / 2.0 * len(b_types))
                b_idx = min(b_idx, len(b_types) - 1)
                
                if self.agent.try_build(b_types[b_idx], self.world):
                    build_success = True


        # Запоминаем состояние до обновления мира
        prev_energy = self.agent.energy
        prev_alive = self.agent.is_alive
        prev_entity_count = len(self.world.entities)
        
        # --- PRE-UPDATE: SmartCreature auto-eat и состав (без поведения) ---
        if self.agent_type == "smart" and self.agent.is_alive:
            # Авто-поедание из инвентаря (мясо/вареное мясо) или растений
            self.agent._auto_eat_from_inventory(self.config.dt, world=self.world)
            # Делимся едой с соплеменниками
            self.agent._share_resources_with_tribe(self.world)
            # Сброс состояния перед шагом (default: idle)
            self.agent.state = "idle"
        
        # --- Обновляем мир (все остальные действуют по эвристике) ---
        # Подменяем behavior RL-агента на пустой, чтобы эвристика не перезаписала velocity
        original_behavior = self.agent.behavior
        self.agent.behavior = lambda dt, world=None: None  # no-op
        
        self.world.update(self.config.dt)
        
        # Восстанавливаем
        self.agent.behavior = original_behavior
        
        # --- POST-UPDATE: Update SmartCreature state based on action ---
        if self.agent_type == "smart" and self.agent.is_alive:
            # Обновляем состояние если был выполнен режим
            if smart_mode == "gather" and gather_contact:
                self.agent.state = "gathering"
            elif smart_mode == "craft":
                self.agent.state = "crafting" if craft_success else "idle"
            elif smart_mode == "build":
                self.agent.state = "building" if build_success else "idle"
        
        # --- Обновляем attack cooldown для RL-хищника ---
        if self.agent_type in ("predator", "smart") and self.agent.is_alive:
            self.agent.attack_timer -= self.config.dt
        
        # --- Авто-атака для RL-хищника ---
        dealt_damage = 0.0
        killed = False
        closest_prey_dist = -1.0
        
        # Smart also attacks like predator if mode is set or auto-attack enabled (let's keep auto-attack for consistency/simplicity)
        if self.agent_type in ("predator", "smart") and self.agent.is_alive:
            # Ищем ближайшую добычу (Optimized)
            best_prey = None
            best_dist_sq = float('inf')
            max_scan_dist_sq = (self.agent.vision_range + 20)**2 # Only scan within vision
            
            # Определяем типы целей
            target_types = set()
            if self.agent_type == "predator":
                target_types = {"herbivore", "smart"}
            elif self.agent_type == "smart":
                target_types = {"herbivore", "predator"}

            agent_pos_x, agent_pos_y = self.agent.pos.x, self.agent.pos.y
            
            for entity in self.world.entities:
                if entity is self.agent or not entity.is_alive:
                    continue
                if entity.entity_type not in target_types:
                    continue
                
                dx = entity.pos.x - agent_pos_x
                dy = entity.pos.y - agent_pos_y
                dist_sq = dx*dx + dy*dy
                
                if dist_sq < best_dist_sq and dist_sq < max_scan_dist_sq:
                    best_dist_sq = dist_sq
                    best_prey = entity
            
            if best_prey is not None:
                import math
                best_dist = math.sqrt(best_dist_sq)
                closest_prey_dist = best_dist
                
                # Атака если в радиусе и cooldown прошёл
                if best_dist < self.agent.attack_range and self.agent.attack_timer <= 0:
                    damage = self.agent.get_damage()
                    best_prey.take_damage(damage)
                    self.agent.energy += damage * 1.5
                    self.agent.attack_timer = self.agent.attack_cooldown
                    dealt_damage = damage
                    if not best_prey.is_alive:
                        killed = True
                        if self.agent_type == "smart":
                             self.agent._on_prey_killed(best_prey, self.world)

        if self.agent_type == "smart" and inv_before is not None and hasattr(self.agent, 'inventory'):
            inv_after = self.agent.inventory.get_contents()
            raw_items = [ItemType.WOOD, ItemType.STONE, ItemType.COPPER_ORE, ItemType.IRON_ORE]
            gather_items_gained = int(sum(
                max(0, inv_after.get(item_t, 0) - inv_before.get(item_t, 0))
                for item_t in raw_items
            ))

        # --- Closest resource for smart shaping ---
        closest_resource_dist = -1.0
        if self.agent_type == "smart" and self.agent.is_alive:
            import math
            best_res_dist_sq = float('inf')
            agent_x, agent_y = self.agent.pos.x, self.agent.pos.y
            vis_sq = self.agent.vision_range ** 2
            for res in self.world.resources:
                if not res.is_alive:
                    continue
                dx = res.pos.x - agent_x
                dy = res.pos.y - agent_y
                d2 = dx * dx + dy * dy
                if d2 < best_res_dist_sq and d2 < vis_sq:
                    best_res_dist_sq = d2
                    closest_resource_dist = math.sqrt(d2) if d2 < vis_sq else -1.0
            if best_res_dist_sq == float('inf'):
                closest_resource_dist = -1.0

        # --- Авто-поедание для RL-травоядного ---
        closest_plant_dist = -1.0
        closest_predator_dist = -1.0
        damage_taken = 0.0
        
        if self.agent_type == "herbivore" and self.agent.is_alive:
            # ... (Old herbivore logic) ...
            best_plant = None
            best_dist = float('inf')
            for plant in self.world.plants:
                if not plant.is_alive:
                    continue
                dist = (plant.pos - self.agent.pos).magnitude()
                if dist < best_dist:
                    best_plant = plant
                    best_dist = dist

            if best_plant is not None:
                closest_plant_dist = best_dist
                if best_dist < 12.0:
                    bite = min(best_plant.energy, (best_plant.max_energy / best_plant.consumption_time) * self.config.dt)
                    if bite > 0:
                        best_plant.energy -= bite
                        self.agent.gain_energy(bite)
                        if best_plant.energy <= 0:
                            best_plant.is_alive = False
            
            # Ближайший хищник
            best_pred_dist = float('inf')
            for entity in self.world.entities:
                if entity.entity_type in ("predator", "smart") and entity.is_alive and entity is not self.agent:
                    dist = (entity.pos - self.agent.pos).magnitude()
                    if dist < best_pred_dist:
                        best_pred_dist = dist
            if best_pred_dist < float('inf'):
                closest_predator_dist = best_pred_dist

        # Calculate Damage Taken
        expected_move_cost = EnergySystem.calculate_movement_cost(
            self.agent.velocity.magnitude(), self.config.dt, self.agent.entity_type
        )
        expected_metabolic = EnergySystem.calculate_metabolic_cost(self.config.dt)
        expected_drop = expected_move_cost + expected_metabolic
        actual_drop = max(0.0, prev_energy - self.agent.energy)
        # Если разница значительная — значит был внешний урон
        if actual_drop > expected_drop + 0.5:
             damage_taken = actual_drop - expected_drop
        
        # --- Вычисляем награду ---
        at_wall = (
            self.agent.pos.x <= 1 or self.agent.pos.x >= self.world.width - 1 or
            self.agent.pos.y <= 1 or self.agent.pos.y >= self.world.height - 1
        )
        
        got_damage = (self.agent.energy < prev_energy - 0.5) and self.agent.is_alive
        reproduced = len(self.world.entities) > prev_entity_count
        
        agent_speed = self.agent.velocity.magnitude()
        displacement = (self.agent.pos - prev_pos).magnitude()

        heading_change = 0.0
        if prev_velocity.magnitude() > 0.1 and self.agent.velocity.magnitude() > 0.1:
            prev_dir = prev_velocity.normalize()
            curr_dir = self.agent.velocity.normalize()
            dot = np.clip(prev_dir.x * curr_dir.x + prev_dir.y * curr_dir.y, -1.0, 1.0)
            heading_change = (1.0 - dot) * 0.5  # 0..1
        
        if self.agent_type == "herbivore":
            reward = RewardCalculator.herbivore_step_reward(
                entity=self.agent,
                prev_energy=prev_energy,
                got_damage=got_damage,
                reproduced=reproduced,
                at_wall=at_wall,
                closest_plant_dist=closest_plant_dist,
                prev_closest_plant_dist=self.prev_closest_plant_dist,
                closest_predator_dist=closest_predator_dist,
                prev_closest_predator_dist=self.prev_closest_predator_dist,
                damage_taken=damage_taken,
                speed=agent_speed,
                displacement=displacement,
                heading_change=heading_change,
            )
            self.prev_closest_plant_dist = closest_plant_dist
            self.prev_closest_predator_dist = closest_predator_dist
            
        elif self.agent_type == "predator":
            reward = RewardCalculator.predator_step_reward(
                entity=self.agent,
                prev_energy=prev_energy,
                dealt_damage=dealt_damage,
                killed_prey=killed,
                reproduced=reproduced,
                at_wall=at_wall,
                closest_prey_dist=closest_prey_dist,
                prev_closest_prey_dist=self.prev_closest_prey_dist,
                speed=agent_speed,
            )
            self.prev_closest_prey_dist = closest_prey_dist
            
        elif self.agent_type == "smart":
            reward = RewardCalculator.smart_step_reward(
                entity=self.agent,
                prev_energy=prev_energy,
                dealt_damage=dealt_damage,
                killed_prey=killed,
                reproduced=reproduced,
                at_wall=at_wall,
                closest_prey_dist=closest_prey_dist,
                prev_closest_prey_dist=self.prev_closest_prey_dist,
                speed=agent_speed,
                gather_contact=(smart_mode == "gather" and gather_contact),
                gather_items_gained=gather_items_gained,
                crafted=craft_success,
                crafted_tier=crafted_tier,
                built=build_success,
                equip_success=equip_success,
                closest_resource_dist=closest_resource_dist,
                prev_closest_resource_dist=self.prev_closest_resource_dist,
            )
            
            self.prev_closest_prey_dist = closest_prey_dist
            self.prev_closest_resource_dist = closest_resource_dist
        
        # --- Завершение эпизода ---
        terminated = not self.agent.is_alive
        truncated = self.current_step >= self.max_steps
        
        obs = self._get_obs()
        info = {
            "energy": self.agent.energy if self.agent.is_alive else 0,
            "age": self.agent.age,
            "step": self.current_step,
        }
        
        self.prev_energy = self.agent.energy
        
        return obs, reward, terminated, truncated, info
    
    def _get_obs(self) -> np.ndarray:
        """Получить observation для RL-агента."""
        if not self.agent.is_alive:
            return np.zeros(self.obs_dim, dtype=np.float32)
        
        sensors = self.agent.get_sensor_data(self.world)
        
        # Self state
        energy_ratio = self.agent.energy / self.agent.max_energy
        speed_mag = self.agent.velocity.magnitude()
        vx_norm = self.agent.velocity.x / max(self.agent.max_speed, 1) if speed_mag > 0 else 0
        vy_norm = self.agent.velocity.y / max(self.agent.max_speed, 1) if speed_mag > 0 else 0
        pos_x_norm = (self.agent.pos.x / max(self.world.width, 1)) * 2 - 1   # -1..1
        pos_y_norm = (self.agent.pos.y / max(self.world.height, 1)) * 2 - 1
        
        self_state = np.array([energy_ratio, vx_norm, vy_norm, pos_x_norm, pos_y_norm], dtype=np.float32)
        
        # Nearby objects
        plants_enc = _encode_nearby(sensors['nearby_plants'], MAX_NEARBY_PLANTS)
        herbs_enc = _encode_nearby_entities(sensors['nearby_herbivores'], MAX_NEARBY_HERBIVORES)
        
        # Для травоядных smart тоже считаем угрозой и кодируем в predator-слоты
        if self.agent_type == "herbivore":
            predator_like = sensors['nearby_predators'] + sensors.get('nearby_smarts', [])
        else:
            # For Smart/Predator, we keep predators separate usually?
            # gym_env logic: simple concatenation
            predator_like = sensors['nearby_predators']
            # Note: Smart agents might want to see other Smarts distinctively?
            # For now in 'predator' slots is fine, or we could add 'allies' channel later.
        
        preds_enc = _encode_nearby_entities(predator_like, MAX_NEARBY_PREDATORS)
        
        basic_obs = np.concatenate([self_state, plants_enc, herbs_enc, preds_enc])
        
        if self.agent_type == "smart":
            # --- Inventory (8 slots) ---
            # Wood, Stone, CopperOre, IronOre, Meat, Leather, CopperIngot, IronIngot
            inv_types = [
                ItemType.WOOD, ItemType.STONE, ItemType.COPPER_ORE, ItemType.IRON_ORE,
                ItemType.MEAT, ItemType.LEATHER, ItemType.COPPER_INGOT, ItemType.IRON_INGOT
            ]
            inv_arr = []
            for t in inv_types:
                count = self.agent.inventory.get_count(t)
                inv_arr.append(min(count / 20.0, 1.0)) # Normalize
            inv_enc = np.array(inv_arr, dtype=np.float32)
            
            # --- Equipped (3 slots) ---
            # Weapon, Tool, Armor. 
            # We map specific items to levels 0.0, 0.5, 1.0
            def get_level(item):
                if not item: return 0.0
                if "copper" in item: return 0.5
                if "iron" in item: return 1.0
                if "stone" in item: return 0.2
                return 0.1
                
            equip_arr = [
                get_level(self.agent.equipped.get('weapon')),
                get_level(self.agent.equipped.get('tool')),
                get_level(self.agent.equipped.get('armor'))
            ]
            equip_enc = np.array(equip_arr, dtype=np.float32)
            
            # --- Resources ---
            # --- Resources (Optimized) ---
            import math
            from core.physics import Vector2
            # Optimized finding of nearby resources
            nearby_resources = []
            agent_x, agent_y = self.agent.pos.x, self.agent.pos.y
            vision_sq = self.agent.vision_range**2
            min_x, max_x = agent_x - self.agent.vision_range, agent_x + self.agent.vision_range
            min_y, max_y = agent_y - self.agent.vision_range, agent_y + self.agent.vision_range

            for res in self.world.resources:
                if not res.is_alive: continue
                # Box check
                if not (min_x <= res.pos.x <= max_x and min_y <= res.pos.y <= max_y):
                    continue

                dx = res.pos.x - agent_x
                dy = res.pos.y - agent_y
                dist_sq = dx*dx + dy*dy
                
                if dist_sq < vision_sq:
                    dist = math.sqrt(dist_sq)
                    nearby_resources.append({
                        'distance': dist,
                        'direction': Vector2(dx/dist, dy/dist) if dist > 0.001 else Vector2(0,0),
                        'resource_type': res.resource_type
                    })
            
            res_enc = _encode_nearby_resources(nearby_resources, MAX_NEARBY_RESOURCES)
            
            # --- Buildings (Optimized) ---
            from core.physics import Vector2
            nearby_buildings = []
            for b in self.world.buildings:
                if b.is_destroyed(): continue
                # Box check
                if not (min_x <= b.x <= max_x and min_y <= b.y <= max_y):
                    continue

                dx = b.x - agent_x
                dy = b.y - agent_y
                dist_sq = dx*dx + dy*dy
                
                if dist_sq < vision_sq:
                    dist = math.sqrt(dist_sq)
                    nearby_buildings.append({
                        'distance': dist,
                        'direction': Vector2(dx/dist, dy/dist) if dist > 0.001 else Vector2(0,0),
                        'type': b.type,
                        'owner_id': b.owner_id,
                        'health_ratio': b.health / b.max_health
                    })
            
            bld_enc = _encode_nearby_buildings(nearby_buildings, MAX_NEARBY_BUILDINGS, self.agent.id)
            
            # Combine all for Smart
            final_obs = np.concatenate([basic_obs, inv_enc, equip_enc, res_enc, bld_enc])
            return np.clip(final_obs, -1.0, 1.0)
            
        else:
            return np.clip(basic_obs, -1.0, 1.0)
    
    def render(self):
        """Render не нужен для training (headless)."""
        pass
    
    def close(self):
        pass


class MultiAgentEnv(SingleAgentEnv):
    """
    Расширение: несколько RL-агентов одного типа в одном мире.
    Для simple-baselines3 мы всё равно обучаем одного агента за раз,
    но этот класс позволяет позже масштабировать.
    """
    
    def __init__(self, agent_type: str = "herbivore",
                 num_rl_agents: int = 3,
                 config: SimulationConfig = None,
                 max_steps: int = 4000):
        super().__init__(agent_type=agent_type, config=config, max_steps=max_steps)
        self.num_rl_agents = num_rl_agents
        # Для MultiAgent используем только первого агента для SB3
        # Остальные RL-агенты используют ту же policy (shared)
