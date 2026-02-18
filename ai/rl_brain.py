"""RL Brain — обёртка для SB3 PPO-модели, реализующая интерфейс Brain."""

import os
import random
import numpy as np
from ai.brain import Brain
from ai.gym_env import MAX_NEARBY_PLANTS, MAX_NEARBY_HERBIVORES, MAX_NEARBY_PREDATORS, _encode_nearby, _encode_nearby_entities


class RLBrain(Brain):
    """
    Мозг, управляемый обученной PPO-моделью (stable-baselines3).
    
    В режиме inference (по умолчанию) — загружает модель и вызывает predict().
    В режиме training используется через gym_env, а не напрямую.
    """
    
    OBS_DIM = 5 + MAX_NEARBY_PLANTS * 4 + MAX_NEARBY_HERBIVORES * 6 + MAX_NEARBY_PREDATORS * 6
    MEMORY_MIN_SEC = 0.10
    MEMORY_MAX_SEC = 0.30
    
    def __init__(self, model_path: str = None, agent_type: str = "herbivore"):
        self.agent_type = agent_type
        self.model = None
        self.model_path = model_path
        self._last_move_dir = {}
        self._decision_memory = {}
        
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)
    
    def _load_model(self, path: str, verbose: bool = True):
        """Загрузить обученную PPO модель."""
        try:
            from stable_baselines3 import PPO
            self.model = PPO.load(path, device="cpu")
            if verbose:
                print(f"[RLBrain] Model loaded from {path}")
        except Exception as e:
            print(f"[RLBrain] Failed to load model from {path}: {e}")
            self.model = None
    
    def _build_observation(self, sensor_data: dict, entity) -> np.ndarray:
        """Преобразовать sensor_data в numpy observation (как в gym_env)."""
        energy_ratio = entity.energy / entity.max_energy if entity.max_energy > 0 else 0
        speed_mag = entity.velocity.magnitude()
        vx_norm = entity.velocity.x / max(entity.max_speed, 1) if speed_mag > 0 else 0
        vy_norm = entity.velocity.y / max(entity.max_speed, 1) if speed_mag > 0 else 0
        # pos нормализация [-1,1] — берём world size из sensor_data если есть
        world_w = sensor_data.get('world_width', 500)
        world_h = sensor_data.get('world_height', 500)
        pos_x_norm = (entity.pos.x / max(world_w, 1)) * 2 - 1
        pos_y_norm = (entity.pos.y / max(world_h, 1)) * 2 - 1
        
        self_state = np.array([energy_ratio, vx_norm, vy_norm, pos_x_norm, pos_y_norm], dtype=np.float32)
        
        plants_enc = _encode_nearby(sensor_data['nearby_plants'], MAX_NEARBY_PLANTS)
        herbs_enc = _encode_nearby_entities(sensor_data['nearby_herbivores'], MAX_NEARBY_HERBIVORES)
        if self.agent_type == "herbivore":
            predator_like = sensor_data.get('nearby_predators', []) + sensor_data.get('nearby_smarts', [])
        elif self.agent_type == "predator":
            # Хищники должны видеть smart-существ как добычу (в канале травоядных)
            # Примечание: это объединяет их, что может быть не идеальным, но позволит модели реагировать
            obs_prey = sensor_data.get('nearby_herbivores', []) + sensor_data.get('nearby_smarts', [])
            herbs_enc = _encode_nearby_entities(obs_prey, MAX_NEARBY_HERBIVORES)
            predator_like = sensor_data.get('nearby_predators', [])
        else:
            predator_like = sensor_data.get('nearby_predators', [])
        preds_enc = _encode_nearby_entities(predator_like, MAX_NEARBY_PREDATORS)
        
        obs = np.concatenate([self_state, plants_enc, herbs_enc, preds_enc])
        return np.clip(obs, -1.0, 1.0)

    def _remember_decision(self, entity, decision: dict, duration: float = None):
        """Сохранить краткосрочное решение для сглаживания поведения."""
        if entity is None:
            return

        hold = duration if duration is not None else random.uniform(self.MEMORY_MIN_SEC, self.MEMORY_MAX_SEC)
        stored = {
            'action': decision.get('action', 'idle'),
            'target': decision.get('target'),
            'speed': float(decision.get('speed', 0)),
            'plant_id': decision.get('plant_id'),
        }
        self._decision_memory[entity.id] = {
            'until_age': entity.age + hold,
            'decision': stored,
        }

    def _recall_decision(self, sensor_data: dict, entity):
        """Вернуть запомненное решение, если окно памяти ещё активно и решение валидно."""
        if entity is None:
            return None

        mem = self._decision_memory.get(entity.id)
        if not mem:
            return None

        if entity.age >= mem['until_age']:
            self._decision_memory.pop(entity.id, None)
            return None

        decision = mem['decision']
        action = decision.get('action', 'idle')

        if action == 'eat':
            plant_id = decision.get('plant_id')
            plants = sensor_data.get('nearby_plants', [])
            plant = next((p for p in plants if p.get('id') == plant_id), None)
            if plant is not None and plant.get('distance', 999.0) <= 16.0:
                return {
                    'action': 'eat',
                    'target': plant.get('direction', decision.get('target')),
                    'speed': 0,
                    'plant_id': plant_id,
                }
            self._decision_memory.pop(entity.id, None)
            return None

        if action == 'move':
            target = decision.get('target')
            if target is not None and target.magnitude() > 0:
                return {
                    'action': 'move',
                    'target': target,
                    'speed': decision.get('speed', 0),
                }
            self._decision_memory.pop(entity.id, None)

        return None
    
    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        """
        Определить действие на основе данных сенсоров.
        
        Если модель не загружена — возвращаем idle.
        entity передаётся дополнительно для построения observation.
        """
        if self.model is None or entity is None:
            return {'action': 'idle', 'target': None, 'speed': 0}
        
        # Для травоядных: короткая память действий (0.1–0.3с),
        # чтобы не дёргаться каждый тик и удерживать поведение.
        # Бегство при угрозе всё равно имеет приоритет выше на уровне Herbivore.behavior.
        if self.agent_type == "herbivore":
            recalled = self._recall_decision(sensor_data, entity)
            if recalled is not None:
                return recalled

            plants = sensor_data.get('nearby_plants', [])
            closest_food = min(plants, key=lambda p: p['distance']) if plants else None

            # Новый вход в режим питания.
            if closest_food and closest_food['distance'] <= 12.0:
                eat_decision = {
                    'action': 'eat',
                    'target': closest_food.get('direction'),
                    'speed': 0,
                    'plant_id': closest_food.get('id'),
                }
                self._remember_decision(entity, eat_decision, duration=random.uniform(0.14, 0.26))
                return eat_decision

        obs = self._build_observation(sensor_data, entity)
        action, _ = self.model.predict(obs, deterministic=True)
        
        # action: [move_x, move_y, speed_factor]
        move_x = float(np.clip(action[0], -1.0, 1.0))
        move_y = float(np.clip(action[1], -1.0, 1.0))
        
        # Хищник: [-1,1] → [0.3, 1.0], травоядное: [0, 1]
        if self.agent_type == "predator":
            speed_factor = 0.3 + 0.7 * (float(np.clip(action[2], -1.0, 1.0)) + 1.0) / 2.0
        else:
            # Для травоядных держим минимальную скорость, чтобы не залипали на месте
            speed_factor = 0.2 + 0.8 * (float(np.clip(action[2], -1.0, 1.0)) + 1.0) / 2.0
        
        from core.physics import Vector2
        direction = Vector2(move_x, move_y)
        mag = direction.magnitude()
        if mag > 0.12:
            direction = direction.normalize()
        elif self.agent_type == "herbivore":
            # Fallback-направление для травоядных, когда policy даёт почти нулевой вектор:
            # 1) убегать от ближайшей угрозы, 2) идти к растению, 3) продолжать текущий курс.
            predator_like = sensor_data.get('nearby_predators', []) + sensor_data.get('nearby_smarts', [])
            plants = sensor_data.get('nearby_plants', [])

            if predator_like and entity.energy > 15:
                threat = min(predator_like, key=lambda p: p['distance'])
                direction = Vector2(-threat['direction'].x, -threat['direction'].y).normalize()
            elif plants:
                food = min(plants, key=lambda p: p['distance'])
                direction = food['direction'].normalize() if food['direction'].magnitude() > 0 else Vector2(1, 0)
            elif entity.velocity.magnitude() > 0.3:
                direction = entity.velocity.normalize()
            else:
                # Вместо случайного вращения (которое выглядит как баг), просто стоим или продолжаем (0,0)
                # Это заставит агента остановиться, если сеть не уверена
                direction = Vector2(0, 0)

        # Пост-обработка движения травоядных для стабильности в inference:
        # 1) отталкивание от края карты, 2) сглаживание резких разворотов.
        if self.agent_type == "herbivore":
            world_w = sensor_data.get('world_width', 500)
            world_h = sensor_data.get('world_height', 500)
            margin = 22.0
            edge_push = Vector2(0.0, 0.0)

            if entity.pos.x < margin:
                edge_push.x += (margin - entity.pos.x) / margin
            elif entity.pos.x > world_w - margin:
                edge_push.x -= (entity.pos.x - (world_w - margin)) / margin

            if entity.pos.y < margin:
                edge_push.y += (margin - entity.pos.y) / margin
            elif entity.pos.y > world_h - margin:
                edge_push.y -= (entity.pos.y - (world_h - margin)) / margin

            if edge_push.magnitude() > 0:
                edge_push = edge_push.normalize()
                if direction.magnitude() > 0:
                    direction = direction * 0.45 + edge_push * 0.55
                else:
                    direction = edge_push

            prev_dir = self._last_move_dir.get(entity.id)
            if prev_dir is not None and prev_dir.magnitude() > 0 and direction.magnitude() > 0:
                direction = prev_dir * 0.65 + direction * 0.35

            if direction.magnitude() > 0:
                direction = direction.normalize()
                self._last_move_dir[entity.id] = direction
        
        decision = {
            'action': 'move',
            'target': direction,
            'speed': speed_factor * entity.max_speed,
        }
        if self.agent_type == "herbivore" and direction.magnitude() > 0:
            self._remember_decision(entity, decision)

        return decision


class RLHerbivoreBrain(RLBrain):
    """PPO brain для травоядных."""
    
    DEFAULT_MODEL = "models/herbivore_ppo.zip"
    
    def __init__(self, model_path: str = None):
        path = model_path or self.DEFAULT_MODEL
        super().__init__(model_path=path, agent_type="herbivore")


class RLPredatorBrain(RLBrain):
    """PPO brain для хищников."""
    
    DEFAULT_MODEL = "models/predator_ppo.zip"
    
    def __init__(self, model_path: str = None):
        path = model_path or self.DEFAULT_MODEL
        super().__init__(model_path=path, agent_type="predator")


class _SharedRLBrain(Brain):
    """
    Лёгкая обёртка — переиспользует уже загруженный RLBrain (shared model).
    Не загружает модель повторно, экономит RAM.
    """
    
    def __init__(self, shared_brain: RLBrain, agent_type: str = "herbivore"):
        self._shared = shared_brain
        self.agent_type = agent_type
    
    def decide_action(self, sensor_data: dict, entity=None) -> dict:
        return self._shared.decide_action(sensor_data, entity=entity)
