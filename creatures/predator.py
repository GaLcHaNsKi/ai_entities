"""Хищные животные"""

from creatures.base import Animal
from core.physics import Vector2
import random


class Predator(Animal):
    """
    Хищное животное
    Цель: найти травоядное и съесть его, выжить как можно дольше
    """
    
    def __init__(self, x: float, y: float, brain=None):
        super().__init__(x, y, entity_type="predator")
        
        # Параметры
        self.radius = 5.0
        self.vision_range = 150.0
        self.max_speed = 100.0
        self.attack_range = 12.0
        self.attack_damage = 40.0  # Больше урона по умолчанию
        self.attack_cooldown = 0.2
        self.attack_timer = 0
        
        # Состояние поведения
        self.state = "idle"  # idle, hunting, attacking, fleeing
        self.current_prey = None
        self.random_direction_timer = 0
        
        # Мозг (pluggable)
        self.brain = brain
        self._is_rl_agent = False
    
    def reproduce(self):
        """Размножение для хищников — потомки получают больше энергии."""
        if not self.can_reproduce():
            return None
        
        reproduction_cost = self.max_energy * 0.4
        self.energy -= reproduction_cost
        self.reproduction_cooldown = 5.0
        
        # Потомок появляется со смещением от родителя
        ox = self.pos.x + random.uniform(-30, 30)
        oy = self.pos.y + random.uniform(-30, 30)
        offspring = Predator(ox, oy, brain=self._clone_brain())
        offspring.energy = reproduction_cost * 1.0
        return offspring
    
    def _clone_brain(self):
        """Создать копию мозга для потомка."""
        if self.brain is None:
            return None
        from ai.rl_brain import _SharedRLBrain
        if isinstance(self.brain, _SharedRLBrain):
            return _SharedRLBrain(self.brain._shared, agent_type=self.brain.agent_type)
        return self.brain.__class__()
    
    def get_damage(self) -> float:
        """
        Расчет урона в зависимости от энергии
        Полная энергия = 1.5x урон
        Половина энергии = 0.75x урон
        Нет энергии = 0.3x урон
        """
        energy_ratio = max(0, self.energy / self.max_energy)
        damage_multiplier = 0.3 + energy_ratio * 1.2
        return self.attack_damage * damage_multiplier
    
    def behavior(self, dt: float, world=None):
        """
        Поведение хищника.
        Если установлен brain — делегируем ему.
        Иначе — legacy hardcoded logic.
        """
        if self._is_rl_agent:
            # RL-агент: velocity уже выставлен извне, но обновляем cooldown
            self.attack_timer -= dt
            return
        
        if world is None:
            return
        
        sensors = self.get_sensor_data(world)
        
        # Обновляем cooldown атаки всегда
        self.attack_timer -= dt
        
        # ---------- Pluggable brain ----------
        if self.brain is not None:
            decision = self.brain.decide_action(sensors, entity=self)
            self._execute_decision(decision, dt, world)
            return
        
        # ---------- Legacy hardcoded behavior ----------
        herbivores = sensors['nearby_herbivores']
        smarts = sensors.get('nearby_smarts', [])
        preys = herbivores + smarts
        predators = sensors['nearby_predators']
        
        # 1. ПОИСК ДОБЫЧИ (травоядные) - приоритет 1
        if preys:
            closest_prey = min(preys, key=lambda h: h['distance'])
            if closest_prey['distance'] < self.attack_range:
                if self.attack_timer <= 0:
                    for entity in world.entities:
                        if entity.id == closest_prey['id']:
                            damage = self.get_damage()
                            entity.take_damage(damage)
                            self.energy += damage * 1.5
                            self.attack_timer = self.attack_cooldown
                            self.state = "attacking"
                            self.current_prey = entity
                            break
            else:
                target_pos = self.pos + closest_prey['direction'] * closest_prey['distance']
                self.move_towards(target_pos, speed=85)
                self.state = "hunting"
                self.current_prey = None
            return
        
        # 2. КОНКУРЕНЦИЯ С ДРУГИМИ ХИЩНИКАМИ
        if predators:
            stronger_predators = [p for p in predators if p['energy'] > self.energy * 1.2]
            if stronger_predators:
                closest_threat = min(stronger_predators, key=lambda p: p['distance'])
                self.flee_from(self.pos + closest_threat['direction'] * 100, speed=75)
                self.state = "fleeing"
                self.current_prey = None
                return
        
        # 3. СЛУЧАЙНОЕ БЛУЖДАНИЕ
        self.random_direction_timer -= dt
        if self.random_direction_timer <= 0:
            self.velocity = Vector2(
                random.uniform(-1, 1),
                random.uniform(-1, 1)
            ).normalize() * 35
            self.random_direction_timer = random.uniform(3, 8)
        self.state = "idle"
    
    def _execute_decision(self, decision: dict, dt: float, world):
        """Применить решение мозга к существу."""
        action = decision.get('action', 'idle')
        target = decision.get('target')
        speed = decision.get('speed', 0)
        
        if action == 'attack':
            prey_id = decision.get('prey_id')
            if prey_id and world and self.attack_timer <= 0:
                for entity in world.entities:
                    if entity.id == prey_id:
                        damage = self.get_damage()
                        entity.take_damage(damage)
                        self.energy += damage * 1.5
                        self.attack_timer = self.attack_cooldown
                        self.state = "attacking"
                        self.current_prey = entity
                        break
        
        elif action == 'flee' and target is not None:
            self.velocity = target * speed
            self.state = "fleeing"
            self.current_prey = None
        
        elif action == 'move' and target is not None:
            direction = target.normalize() if target.magnitude() > 0 else Vector2(0, 0)
            target_vel = direction * speed
            # Сглаживание скорости — предотвращает кручение на месте
            lerp = 0.3
            self.velocity = Vector2(
                self.velocity.x + (target_vel.x - self.velocity.x) * lerp,
                self.velocity.y + (target_vel.y - self.velocity.y) * lerp,
            )
            self.state = "hunting"
            self.current_prey = None
            
            # Авто-атака: если добыча в радиусе — бьём (RL-мозг не умеет атаковать явно)
            if world and self.attack_timer <= 0:
                for entity in world.entities:
                    if entity.entity_type in ("herbivore", "smart") and entity.is_alive:
                        dist = (entity.pos - self.pos).magnitude()
                        if dist < self.attack_range:
                            damage = self.get_damage()
                            entity.take_damage(damage)
                            self.energy += damage * 1.5
                            self.attack_timer = self.attack_cooldown
                            self.state = "attacking"
                            self.current_prey = entity
                            break
        
        elif action == 'wander':
            self.random_direction_timer -= dt if hasattr(self, '_last_dt') else 0.016
            if self.random_direction_timer <= 0:
                self.velocity = Vector2(
                    random.uniform(-1, 1), random.uniform(-1, 1)
                ).normalize() * speed
                self.random_direction_timer = random.uniform(3, 8)
            self.state = "idle"
        
        else:  # idle
            self.stop()
            self.state = "idle"
    
    def update(self, dt: float, world=None):
        """Обновление хищника"""
        super().update(dt, world)
        
        if self.can_reproduce():
            offspring = self.reproduce()
            if offspring and world:
                world.add_entity(offspring)
