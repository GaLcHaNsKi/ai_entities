"""Система наград для обучения с подкреплением"""

import numpy as np


class RewardCalculator:
    """
    Вычисляет награды для RL-агентов на основе событий в симуляции.
    
    Каждый агент накапливает reward за шаг, который потом передаётся в gym env.
    """
    
    # === Награды для травоядных ===
    HERBIVORE_EAT_REWARD = 1.5          # Получил энергию от растения (было 1.0)
    HERBIVORE_SURVIVAL_REWARD = 0.01    # Бонус за каждый шаг жизни
    HERBIVORE_REPRODUCE_REWARD = 10.0   # Успешно размножился (было 5.0 — это главная цель!)
    HERBIVORE_DEATH_PENALTY = -10.0     # Умер
    HERBIVORE_DAMAGE_PENALTY = -2.0     # Получил урон
    HERBIVORE_DAMAGE_COEF = -0.35       # Доп. штраф за величину урона
    HERBIVORE_LOW_ENERGY_PENALTY = -0.05  # Энергия < 30%
    HERBIVORE_WALL_PENALTY = -0.1       # Столкнулся со стеной мира
    HERBIVORE_PROXIMITY_REWARD = 0.08   # За близость к растению
    HERBIVORE_APPROACH_REWARD = 0.12    # За сокращение дистанции до растения
    HERBIVORE_ESCAPE_REWARD = 0.20      # За увеличение дистанции от хищника (было 0.16)
    HERBIVORE_IDLE_COEF = -0.05         # Штраф за медленное движение (было -0.03)
    HERBIVORE_STALL_PENALTY = -0.08     # Двигался по velocity, но почти не сменил позицию
    HERBIVORE_SPIN_PENALTY = -0.10      # Резко меняет курс без прогресса (крутится)
    HERBIVORE_PROGRESS_REWARD = 0.05    # Микробонус за реальное перемещение
    
    # === Награды для хищников ===
    PREDATOR_KILL_REWARD = 10.0         # Убил добычу
    PREDATOR_ATTACK_REWARD = 4.0        # Нанёс урон
    PREDATOR_SURVIVAL_REWARD = 0.0      # Убран — мешал, агент учился стоять
    PREDATOR_REPRODUCE_REWARD = 5.0     # Успешно размножился
    PREDATOR_DEATH_PENALTY = -10.0      # Умер
    PREDATOR_HUNGER_PENALTY = -0.08     # Энергия < 30%
    PREDATOR_WALL_PENALTY = -0.1        # Столкнулся со стеной мира
    PREDATOR_PROXIMITY_REWARD = 0.15    # За нахождение рядом с добычей
    PREDATOR_APPROACH_REWARD = 0.20     # За сокращение дистанции до добычи
    PREDATOR_IDLE_COEF = -0.05          # Коэф штрафа за медленное движение

    # === Награды для разумных ===
    SMART_KILL_REWARD = 8.0
    SMART_ATTACK_REWARD = 2.8
    SMART_REPRODUCE_REWARD = 6.0
    SMART_DEATH_PENALTY = -10.0
    SMART_HUNGER_PENALTY = -0.08
    SMART_WALL_PENALTY = -0.10
    SMART_PROXIMITY_REWARD = 0.10
    SMART_APPROACH_REWARD = 0.14
    SMART_IDLE_COEF = -0.035
    SMART_GATHER_CONTACT_REWARD = 0.25
    SMART_GATHER_ITEM_REWARD = 0.45
    SMART_CRAFT_REWARD = 1.8
    SMART_CRAFT_TIER_BONUS = 0.55
    SMART_BUILD_REWARD = 3.0
    SMART_EQUIP_REWARD = 0.6
    
    @staticmethod
    def herbivore_step_reward(entity, prev_energy: float, got_damage: bool,
                               reproduced: bool, at_wall: bool,
                               closest_plant_dist: float = -1.0,
                               prev_closest_plant_dist: float = -1.0,
                               closest_predator_dist: float = -1.0,
                               prev_closest_predator_dist: float = -1.0,
                               damage_taken: float = 0.0,
                               speed: float = 0.0,
                               displacement: float = 0.0,
                               heading_change: float = 0.0) -> float:
        """
        Рассчитать награду травоядного за один шаг.
        
        Args:
            entity: существо Herbivore
            prev_energy: энергия на предыдущем шаге
            got_damage: получил ли урон на этом шаге
            reproduced: размножился ли на этом шаге
            at_wall: находится ли у границы мира
        
        Returns:
            float: суммарная награда за шаг
        """
        reward = 0.0
        
        # Награда за жизнь
        if entity.is_alive:
            reward += RewardCalculator.HERBIVORE_SURVIVAL_REWARD
        else:
            reward += RewardCalculator.HERBIVORE_DEATH_PENALTY
            return reward
        
        # Награда за получение энергии (от еды)
        energy_gained = entity.energy - prev_energy
        if energy_gained > 0:
            reward += RewardCalculator.HERBIVORE_EAT_REWARD * (energy_gained / 20.0)

        # Шейпинг по растениям: близость + прогресс приближения
        if closest_plant_dist >= 0:
            vision = getattr(entity, 'vision_range', 60.0)
            proximity_bonus = max(0.0, 1.0 - closest_plant_dist / max(vision, 1.0))
            reward += RewardCalculator.HERBIVORE_PROXIMITY_REWARD * proximity_bonus

            if prev_closest_plant_dist >= 0:
                dist_delta = prev_closest_plant_dist - closest_plant_dist
                reward += RewardCalculator.HERBIVORE_APPROACH_REWARD * np.clip(dist_delta / 1.5, -1.0, 1.0)

        # Награда за успешное убегание от хищника (дистанция растет)
        if closest_predator_dist >= 0 and prev_closest_predator_dist >= 0:
            predator_delta = closest_predator_dist - prev_closest_predator_dist
            reward += RewardCalculator.HERBIVORE_ESCAPE_REWARD * np.clip(predator_delta / 2.0, -1.0, 1.0)

        # Штраф за медленное движение (чтобы не стоял)
        max_speed = getattr(entity, 'max_speed', 80.0)
        speed_ratio = min(speed / max(max_speed, 1.0), 1.0)
        reward += RewardCalculator.HERBIVORE_IDLE_COEF * (1.0 - speed_ratio)

        # Анти-stall: скорость есть, а перемещения почти нет
        # (типично при толкании стенки или "дрожании" на месте)
        if speed_ratio > 0.25 and displacement < 0.35:
            reward += RewardCalculator.HERBIVORE_STALL_PENALTY

        # Анти-spin: резкие развороты без прогресса
        if heading_change > 0.70 and displacement < 0.8:
            reward += RewardCalculator.HERBIVORE_SPIN_PENALTY

        # Слабый бонус за факт полезного движения
        reward += RewardCalculator.HERBIVORE_PROGRESS_REWARD * min(displacement / 1.0, 1.0)
        
        # Штраф за получение урона
        if got_damage:
            reward += RewardCalculator.HERBIVORE_DAMAGE_PENALTY
        if damage_taken > 0:
            reward += RewardCalculator.HERBIVORE_DAMAGE_COEF * min(damage_taken / 8.0, 2.0)
        
        # Награда за размножение
        if reproduced:
            reward += RewardCalculator.HERBIVORE_REPRODUCE_REWARD
        
        # Штраф за низкую энергию
        energy_ratio = entity.energy / entity.max_energy
        if energy_ratio < 0.3:
            reward += RewardCalculator.HERBIVORE_LOW_ENERGY_PENALTY
        
        # Штраф за столкновение с границей
        if at_wall:
            reward += RewardCalculator.HERBIVORE_WALL_PENALTY
        
        return reward
    
    @staticmethod
    def predator_step_reward(entity, prev_energy: float, dealt_damage: float,
                              killed_prey: bool, reproduced: bool, at_wall: bool,
                              closest_prey_dist: float = -1.0, prev_closest_prey_dist: float = -1.0,
                              speed: float = 0.0) -> float:
        """
        Рассчитать награду хищника за один шаг.
        
        Args:
            entity: существо Predator
            prev_energy: энергия на предыдущем шаге
            dealt_damage: количество нанесённого урона
            killed_prey: убил ли добычу
            reproduced: размножился ли
            at_wall: находится ли у границы мира
            closest_prey_dist: расстояние до ближайшей добычи (-1 если нет)
            speed: текущая скорость агента
        
        Returns:
            float: суммарная награда за шаг
        """
        reward = 0.0
        
        # Награда за жизнь (убрана — вызывала reward hacking)
        if not entity.is_alive:
            reward += RewardCalculator.PREDATOR_DEATH_PENALTY
            return reward
        
        # Награда за нанесение урона
        if dealt_damage > 0:
            reward += RewardCalculator.PREDATOR_ATTACK_REWARD * (dealt_damage / 30.0)
        
        # Награда за убийство добычи
        if killed_prey:
            reward += RewardCalculator.PREDATOR_KILL_REWARD
        
        # Награда за размножение
        if reproduced:
            reward += RewardCalculator.PREDATOR_REPRODUCE_REWARD
        
        # Награда за приближение к добыче
        if closest_prey_dist >= 0:
            # Чем ближе — тем больше (максимум при distance=0)
            vision = getattr(entity, 'vision_range', 150.0)
            proximity_bonus = max(0, 1.0 - closest_prey_dist / vision)
            reward += RewardCalculator.PREDATOR_PROXIMITY_REWARD * proximity_bonus
            
            # Бонус за сокращение дистанции (delta shaping)
            if prev_closest_prey_dist >= 0:
                dist_delta = prev_closest_prey_dist - closest_prey_dist
                # dist_delta > 0 = приближаемся, < 0 = удаляемся
                # Нормируем на 2.0 (реальный макс за шаг ~1.6px)
                reward += RewardCalculator.PREDATOR_APPROACH_REWARD * np.clip(dist_delta / 2.0, -1.0, 1.0)
        
        # Штраф пропорциональный медленному движению
        max_speed = getattr(entity, 'max_speed', 100.0)
        speed_ratio = min(speed / max(max_speed, 1.0), 1.0)
        reward += RewardCalculator.PREDATOR_IDLE_COEF * (1.0 - speed_ratio)
        
        # Штраф за голод
        energy_ratio = entity.energy / entity.max_energy
        if energy_ratio < 0.3:
            reward += RewardCalculator.PREDATOR_HUNGER_PENALTY
        
        # Штраф за столкновение с границей
        if at_wall:
            reward += RewardCalculator.PREDATOR_WALL_PENALTY
        
        return reward

    @staticmethod
    def smart_step_reward(entity, prev_energy: float, dealt_damage: float,
                          killed_prey: bool, reproduced: bool, at_wall: bool,
                          closest_prey_dist: float = -1.0, prev_closest_prey_dist: float = -1.0,
                          speed: float = 0.0,
                          gather_contact: bool = False,
                          gather_items_gained: int = 0,
                          crafted: bool = False,
                          crafted_tier: int = 0,
                          built: bool = False,
                          equip_success: bool = False,
                          closest_resource_dist: float = -1.0,
                          prev_closest_resource_dist: float = -1.0) -> float:
        """Награда для smart-агента: выживание + бой + экономика (добыча/крафт/стройка)."""
        reward = 0.0

        if not entity.is_alive:
            return RewardCalculator.SMART_DEATH_PENALTY

        if dealt_damage > 0:
            reward += RewardCalculator.SMART_ATTACK_REWARD * (dealt_damage / 30.0)

        if killed_prey:
            reward += RewardCalculator.SMART_KILL_REWARD

        if reproduced:
            reward += RewardCalculator.SMART_REPRODUCE_REWARD

        if closest_prey_dist >= 0:
            vision = getattr(entity, 'vision_range', 95.0)
            proximity_bonus = max(0.0, 1.0 - closest_prey_dist / max(vision, 1.0))
            reward += RewardCalculator.SMART_PROXIMITY_REWARD * proximity_bonus

            if prev_closest_prey_dist >= 0:
                dist_delta = prev_closest_prey_dist - closest_prey_dist
                reward += RewardCalculator.SMART_APPROACH_REWARD * np.clip(dist_delta / 2.0, -1.0, 1.0)

        max_speed = getattr(entity, 'max_speed', 88.0)
        speed_ratio = min(speed / max(max_speed, 1.0), 1.0)
        reward += RewardCalculator.SMART_IDLE_COEF * (1.0 - speed_ratio)

        energy_ratio = entity.energy / max(entity.max_energy, 1.0)
        if energy_ratio < 0.25:
            reward += RewardCalculator.SMART_HUNGER_PENALTY

        if at_wall:
            reward += RewardCalculator.SMART_WALL_PENALTY

        if gather_contact:
            reward += RewardCalculator.SMART_GATHER_CONTACT_REWARD
        if gather_items_gained > 0:
            reward += RewardCalculator.SMART_GATHER_ITEM_REWARD * min(gather_items_gained, 5)

        if crafted:
            reward += RewardCalculator.SMART_CRAFT_REWARD
            reward += RewardCalculator.SMART_CRAFT_TIER_BONUS * max(0, crafted_tier)

        if built:
            reward += RewardCalculator.SMART_BUILD_REWARD

        if equip_success:
            reward += RewardCalculator.SMART_EQUIP_REWARD

        return reward
