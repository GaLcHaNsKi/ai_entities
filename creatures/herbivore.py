"""Травоядные животные"""

from creatures.base import Animal
from core.physics import Vector2
import random


class Herbivore(Animal):
    """
    Травоядное животное
    Цель: найти растение и поесть, выжить как можно дольше
    """
    
    def __init__(self, x: float, y: float, brain=None):
        super().__init__(x, y, entity_type="herbivore")
        
        # Параметры
        self.radius = 4.0
        self.vision_range = 60.0
        self.max_speed = 80.0
        
        # Состояние поведения
        self.state = "idle"  # idle, searching, eating, fleeing
        self.eating_plant = None
        self.flee_target = None
        self.random_direction_timer = 0
        self.panic_timer = 0.0
        self.panic_enter_distance = 34.0
        self.panic_exit_distance = 52.0
        self.panic_min_duration = 1.2
        self.post_flee_no_eat_timer = 0.0
        
        # Мозг (pluggable)
        self.brain = brain  # None → legacy hardcoded behavior
        self._is_rl_agent = False  # флаг для gym_env (RL-агент, behavior=no-op)
    
    def behavior(self, dt: float, world=None):
        """
        Поведение травоядного.
        Если установлен brain — делегируем ему.
        Иначе — legacy hardcoded logic.
        """
        if self._is_rl_agent:
            # RL-агент: velocity уже выставлен извне через gym_env.step()
            return
        
        if world is None:
            return
        
        sensors = self.get_sensor_data(world)
        predators = sensors['nearby_predators'] + sensors.get('nearby_smarts', [])
        plants = sensors['nearby_plants']
        # OPTIMIZED: Sensor data уже отсортирован - берём первый элемент вместо min()
        closest_predator = predators[0] if predators else None

        self.post_flee_no_eat_timer = max(0.0, self.post_flee_no_eat_timer - dt)

        # Гистерезис страха: входим в панику рано, выходим поздно + таймер удержания
        if closest_predator and self.energy > 20 and closest_predator['distance'] <= self.panic_enter_distance:
            self.panic_timer = self.panic_min_duration
        elif closest_predator and self.energy > 20 and closest_predator['distance'] <= self.panic_exit_distance:
            self.panic_timer = max(self.panic_timer, 0.5)
        else:
            self.panic_timer = max(0.0, self.panic_timer - dt)
        
        # ---------- Pluggable brain ----------
        if self.brain is not None:
            if closest_predator and self.panic_timer > 0 and self.energy > 20:
                flee_dir = Vector2(-closest_predator['direction'].x, -closest_predator['direction'].y)
                decision = {'action': 'flee', 'target': flee_dir, 'speed': 65}
                self._execute_decision(decision, dt, world)
                return
            decision = self.brain.decide_action(sensors, entity=self)
            self._execute_decision(decision, dt, world)
            return
        
        # ---------- Legacy hardcoded behavior ----------
        # 1. БЕГСТВО от хищников (приоритет 1)
        if closest_predator and self.panic_timer > 0 and self.energy > 20:
            self.flee_from(self.pos + closest_predator['direction'] * 100, speed=65)
            self.state = "fleeing"
            if self.eating_plant:
                self.stop_eating_plant(self.eating_plant)
                self.eating_plant = None
            return
        
        # 2. ПОИСК ЕДЫ (приоритет 2)
        if plants:
            # OPTIMIZED: Берём первый элемент (уже отсортирован по расстоянию)
            closest_plant = plants[0]
            if closest_plant['distance'] < 12:
                plant_obj = None
                for p in world.plants:
                    if p.id == closest_plant['id']:
                        plant_obj = p
                        break
                if plant_obj and plant_obj.is_alive:
                    if self.eating_plant != plant_obj:
                        if self.eating_plant:
                            self.stop_eating_plant(self.eating_plant)
                        self.eating_plant = plant_obj
                        self.eat_plant(plant_obj, dt)
                    self.stop()
                    self.state = "eating"
                    return
            else:
                target_pos = self.pos + closest_plant['direction'] * closest_plant['distance']
                self.move_towards(target_pos, speed=50)
                self.state = "searching"
                if self.eating_plant:
                    self.stop_eating_plant(self.eating_plant)
                    self.eating_plant = None
                return
        
        # 3. СЛУЧАЙНОЕ БЛУЖДАНИЕ
        self.random_direction_timer -= dt
        if self.random_direction_timer <= 0:
            self.velocity = Vector2(
                random.uniform(-1, 1),
                random.uniform(-1, 1)
            ).normalize() * 25
            self.random_direction_timer = random.uniform(2, 5)
        self.state = "idle"
    
    def _execute_decision(self, decision: dict, dt: float, world):
        """Применить решение мозга к существу."""
        action = decision.get('action', 'idle')
        target = decision.get('target')
        speed = decision.get('speed', 0)
        
        if action == 'flee' and target is not None:
            self.velocity = target * speed
            self.state = "fleeing"
            self.post_flee_no_eat_timer = max(self.post_flee_no_eat_timer, 0.9)
            if self.eating_plant:
                self.stop_eating_plant(self.eating_plant)
                self.eating_plant = None
        
        elif action == 'eat':
            if self.post_flee_no_eat_timer > 0:
                return
            plant_id = decision.get('plant_id')
            if plant_id and world:
                plant_obj = None
                for p in world.plants:
                    if p.id == plant_id:
                        plant_obj = p
                        break
                if plant_obj and plant_obj.is_alive:
                    if self.eating_plant != plant_obj:
                        if self.eating_plant:
                            self.stop_eating_plant(self.eating_plant)
                        self.eating_plant = plant_obj
                        self.eat_plant(plant_obj, dt)
                    self.stop()
                    self.state = "eating"
                    return
            self.stop()
            self.state = "eating"
        
        elif action == 'move' and target is not None:
            direction = target.normalize() if target.magnitude() > 0 else Vector2(0, 0)
            target_vel = direction * speed
            # Сглаживание скорости — предотвращает кручение на месте
            lerp = 0.3
            self.velocity = Vector2(
                self.velocity.x + (target_vel.x - self.velocity.x) * lerp,
                self.velocity.y + (target_vel.y - self.velocity.y) * lerp,
            )
            self.state = "searching"
            if self.eating_plant:
                self.stop_eating_plant(self.eating_plant)
                self.eating_plant = None
        
        elif action == 'wander':
            self.random_direction_timer -= dt if hasattr(self, '_last_dt') else 0.016
            if self.random_direction_timer <= 0:
                self.velocity = Vector2(
                    random.uniform(-1, 1), random.uniform(-1, 1)
                ).normalize() * speed
                self.random_direction_timer = random.uniform(2, 5)
            self.state = "idle"
        
        else:  # idle
            self.stop()
            self.state = "idle"
    
    def update(self, dt: float, world=None):
        """Обновление травоядного"""
        super().update(dt, world)
        
        # Проверяем размножение
        if self.can_reproduce():
            offspring = self.reproduce()
            if offspring and world:
                world.add_entity(offspring)
    
    def reproduce(self):
        """Размножение — потомок наследует тип мозга."""
        if not self.can_reproduce():
            return None
        
        reproduction_cost = self.max_energy * 0.4
        self.energy -= reproduction_cost
        self.reproduction_cooldown = 5.0
        
        # Потомок появляется со смещением от родителя
        ox = self.pos.x + random.uniform(-25, 25)
        oy = self.pos.y + random.uniform(-25, 25)
        offspring = Herbivore(ox, oy, brain=self._clone_brain())
        offspring.energy = reproduction_cost * 0.8
        return offspring
    
    def _clone_brain(self):
        """Создать копию мозга для потомка."""
        if self.brain is None:
            return None
        # _SharedRLBrain — переиспользуем тот же shared объект
        from ai.rl_brain import _SharedRLBrain
        if isinstance(self.brain, _SharedRLBrain):
            return _SharedRLBrain(self.brain._shared, agent_type=self.brain.agent_type)
        # Для эвристики — просто новый экземпляр того же класса
        return self.brain.__class__()
