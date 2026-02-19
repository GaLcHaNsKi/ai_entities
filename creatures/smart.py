"""Разумное существо: племя, совместная охота, инвентарь, крафт."""

import random
from creatures.base import Animal
from core.physics import Vector2
from core.items import ItemType, ITEM_DB, ItemCategory
from core.inventory import Inventory
from core.crafting import CraftingSystem
from core.building import BuildingType, BUILDING_DB

class SmartCreature(Animal):
    """Разумное существо: охотится вместе, хранит ресурсы, крафтит инструменты."""

    def __init__(self, x: float, y: float, brain=None):
        super().__init__(x, y, entity_type="smart")

        self.radius = 4.5
        self.vision_range = 95.0
        self.max_speed = 88.0

        self.attack_range = 10.0
        self.attack_damage = 18.0
        self.attack_cooldown = 0.45
        self.attack_timer = 0.0

        self.state = "idle"
        self.current_target = None
        self.eating_plant = None
        self.random_direction_timer = 0.0

        self.brain = brain

        # Племя
        self.tribe_id = 1
        self.pack_vision_radius = 80.0
        self.pack_attack_radius = 55.0
        self.pack_share_radius = 42.0
        self.pack_loot_radius = 45.0

        # Инвентарь и крафт
        self.inventory = Inventory(capacity=35.0)
        self.equipped = {
            'weapon': None,  # ItemType
            'tool': None,    # ItemType
            'armor': None,   # ItemType
            'bag': None      # ItemType
        }
        
        self.memory = {
            'resources': {}, # {(x,y): type} -> запоминает координаты ресурсов
            'dropped_items': [] # [(x,y, type)]
        }
        
        # Таймеры
        self.gather_timer = 0.0
        self.craft_cooldown = 0.0

    def _clone_brain(self):
        if self.brain is None:
            return None
        from ai.rl_brain import _SharedRLBrain
        if isinstance(self.brain, _SharedRLBrain):
            return _SharedRLBrain(self.brain._shared, agent_type=self.brain.agent_type)
        return self.brain.__class__()

    def get_damage(self) -> float:
        """Расчет урона с учетом оружия"""
        base_dmg = self.attack_damage
        
        # Бонус от оружия
        weapon_type = self.equipped.get('weapon')
        if weapon_type:
            stats = ITEM_DB.get(weapon_type)
            if stats:
                base_dmg = stats.damage
                
        # Бонус от энергии
        energy_ratio = max(0.0, self.energy / max(self.max_energy, 1.0))
        return base_dmg * (0.5 + 0.6 * energy_ratio)
        
    def get_mining_efficiency(self) -> float:
        """Эффективность добычи"""
        tool_type = self.equipped.get('tool')
        if tool_type:
            stats = ITEM_DB.get(tool_type)
            if stats:
                return stats.efficiency
        return 1.0

    def get_defense(self) -> float:
        """Защита (0.0 - 1.0)"""
        armor_type = self.equipped.get('armor')
        if armor_type:
            stats = ITEM_DB.get(armor_type)
            if stats:
                return stats.defense
        return 0.0
        
    def take_damage(self, amount: float):
        """Переопределяем получение урона с учетом брони"""
        defense = self.get_defense()
        final_damage = amount * (1.0 - defense)
        super().take_damage(final_damage)

    def _nearby_tribe_members(self, world, radius: float):
        """
        Найти соплеменников в радиусе.
        OPTIMIZED: Использует spatial search вместо полного перебора племени.
        """
        if not hasattr(world, 'smart_tribes'):
            return []
        
        tribe_list = world.smart_tribes.get(self.tribe_id, [])
        if not tribe_list:
            return []
        
        # OPTIMIZED: Используем spatial search вместо O(T) перебора
        members = world.get_entities_in_radius(self.pos, radius, exclude_id=self.id)
        
        # Фильтруем - только живые соплеменники
        result = []
        for entity, dist in members:
            if entity.entity_type == "smart" and entity.tribe_id == self.tribe_id:
                result.append((entity, dist))
        
        return result
        
    def _share_resources_with_tribe(self, world):
        """Делимся едой и ресурсами с соплеменниками"""
        # Prioritize Cooked Meat
        for meat_type in [ItemType.COOKED_MEAT, ItemType.MEAT]:
             meat_count = self.inventory.get_count(meat_type)
             if meat_count <= 0:
                 continue
                 
             for ally, _ in self._nearby_tribe_members(world, self.pack_share_radius):
                if not ally.is_alive: continue
                ally_energy = ally.energy / ally.max_energy
                if ally_energy < 0.4:
                    # Отдаем 1 кусок мяса
                    if self.inventory.remove_item(meat_type, 1):
                        ally.inventory.add_item(meat_type, 1)
                        meat_count -= 1
                        if meat_count <= 0:
                            break
             if meat_count <= 0:
                 break

    def _auto_eat_from_inventory(self, dt: float, world=None):
        """Есть еду из инвентаря, если голоден. Если мяса нет - может съесть растение поблизости."""
        if self.energy < self.max_energy * 0.7:
            # 1. Try Cooked Meat
            if self.inventory.has_item(ItemType.COOKED_MEAT, 1):
                self.inventory.remove_item(ItemType.COOKED_MEAT, 1)
                stats = ITEM_DB[ItemType.COOKED_MEAT]
                self.gain_energy(stats.edible.energy)
                return

            # 2. Try Raw Meat
            if self.inventory.has_item(ItemType.MEAT, 1):
                self.inventory.remove_item(ItemType.MEAT, 1)
                self.gain_energy(25.0)
                return
            
            # 3. If no meat, try to eat nearby plants (omnivore behavior)
            # OPTIMIZED: use spatial search instead of O(N) iteration
            if world is not None:
                plants_nearby = world.get_plants_in_radius(self.pos, radius=15.0)
                if plants_nearby:
                    best_plant, best_dist = plants_nearby[0]  # Already sorted by distance
                    if best_plant.is_alive:
                        # Eat from nearby plant
                        bite = min(best_plant.energy, (best_plant.max_energy / best_plant.consumption_time) * dt)
                        if bite > 0:
                            best_plant.energy -= bite
                            self.gain_energy(bite)
                        if best_plant.energy <= 0:
                            best_plant.is_alive = False
                        return

    def _on_prey_killed(self, prey, world):
        """Лут с убитого врага"""
        # Мясо
        if prey.entity_type == "predator":
            meat_amt = random.randint(2, 4)
            leather_amt = random.randint(1, 2)
        elif prey.entity_type == "herbivore":
            meat_amt = random.randint(1, 3)
            leather_amt = random.randint(1, 2)
        else:
            meat_amt = 1
            leather_amt = 0
            
        # Даем себе
        self.inventory.add_item(ItemType.MEAT, meat_amt)
        if leather_amt > 0:
            self.inventory.add_item(ItemType.LEATHER, leather_amt)

    def reproduce(self):
        if not self.can_reproduce():
            return None

        reproduction_cost = self.max_energy * 0.4
        self.energy -= reproduction_cost
        self.reproduction_cooldown = 5.0

        ox = self.pos.x + random.uniform(-25, 25)
        oy = self.pos.y + random.uniform(-25, 25)
        offspring = SmartCreature(ox, oy, brain=self._clone_brain())
        offspring.tribe_id = self.tribe_id
        offspring.reproduction_energy_threshold = self.reproduction_energy_threshold
        offspring.energy = reproduction_cost * 0.85
        # Передаем немного еды
        if self.inventory.remove_item(ItemType.MEAT, 2):
            offspring.inventory.add_item(ItemType.MEAT, 2)
        return offspring

    def update(self, dt: float, world=None):
        """Обновление smart-существа + размножение."""
        super().update(dt, world)

        if self.can_reproduce():
            offspring = self.reproduce()
            if offspring and world:
                world.add_entity(offspring)

    def gather_resource(self, resource_node, dt: float):
        """Добыча статического ресурса (дерево, камень)"""
        if not resource_node.is_alive: return False
        
        # 1. Проверяем расстояние
        dist = (self.pos - resource_node.pos).magnitude()
        if dist > 15.0:
            return False # Too far
            
        # 2. Добавляем себя майнером
        resource_node.add_miner(self.id, efficiency=self.get_mining_efficiency())
        return True
        
    def try_craft(self, recipe_result_type: str) -> bool:
        """Попытка скрафтить предмет"""
        from core.crafting import RECIPES
        target_recipe = None
        for r in RECIPES:
            if r.result == recipe_result_type:
                target_recipe = r
                break
        
        if not target_recipe:
            return False
            
        if CraftingSystem.craft(target_recipe, self.inventory):
            return True
        return False

    def try_build(self, b_type_name: str, world) -> bool:
        """Попытка построить здание"""
        try:
            b_type = BuildingType(b_type_name)
        except ValueError:
            return False
            
        stats = BUILDING_DB.get(b_type)
        if not stats:
            return False
            
        # Check cost
        for mat, amt in stats.cost.items():
            if not self.inventory.has_item(mat, amt):
                return False
                
        # Try to place
        new_building = world.add_building(b_type, self.pos.x, self.pos.y, self.id)
        if new_building:
            # Consume resources
            for mat, amt in stats.cost.items():
                self.inventory.remove_item(mat, amt)
            return True
            
        return False
        
    def try_equip(self, item_type: str) -> bool:
        """Экипировать предмет"""
        if not self.inventory.has_item(item_type, 1):
            return False
            
        stats = ITEM_DB.get(item_type)
        if not stats:
            return False
            
        slot = None
        if stats.category == ItemCategory.WEAPON:
            slot = 'weapon'
        elif stats.category == ItemCategory.TOOL:
            slot = 'tool'
        elif stats.category == ItemCategory.ARMOR:
            if item_type == ItemType.LEATHER_BAG:
                slot = 'bag'
            else:
                slot = 'armor'
                
        if slot:
            current = self.equipped.get(slot)
            if current:
                self.inventory.add_item(current, 1)
                
            if self.inventory.remove_item(item_type, 1):
                self.equipped[slot] = item_type
                if slot == 'bag' and stats.carry_bonus:
                    self.inventory.capacity_modifier = stats.carry_bonus    
                return True
        return False

    def _find_entity_by_id(self, world, entity_id: str):
        for entity in world.entities:
            if entity.id == entity_id and entity.is_alive:
                return entity
        return None

    def _try_attack_target(self, world, target_entity) -> bool:
        if target_entity is None or not target_entity.is_alive:
            return False
        if self.attack_timer > 0:
            return False

        dist = (target_entity.pos - self.pos).magnitude()
        if dist >= self.attack_range:
            return False

        damage = self.get_damage()
        target_entity.take_damage(damage)
        self.energy += damage * 0.5
        self.attack_timer = self.attack_cooldown
        self.state = "attacking"
        self.current_target = target_entity

        if not target_entity.is_alive:
            self._on_prey_killed(target_entity, world)
        return True
        
    def _apply_movement(self, direction: Vector2, speed: float):
        target_vel = direction * speed
        lerp = 0.3
        self.velocity = Vector2(
            self.velocity.x + (target_vel.x - self.velocity.x) * lerp,
            self.velocity.y + (target_vel.y - self.velocity.y) * lerp,
        )

    def _execute_decision(self, decision: dict, dt: float, world):
        action = decision.get('action', 'idle')
        target = decision.get('target') # Vector2 direction
        speed = decision.get('speed', 0)
        
        # Movement
        if target is not None and isinstance(target, Vector2):
            self.velocity = target.normalize() * speed
        elif target is None:
            pass 
            
        # Actions
        if action == 'gather':
             target_res_id = decision.get('target_id')
             if target_res_id and world:
                res_node = None
                for res in world.resources:
                    if res.id == target_res_id and res.is_alive:
                        res_node = res
                        break
                if res_node:
                    self.gather_resource(res_node, dt)
                    self.state = "gathering"
                    return
                  
        elif action == 'craft':
            item_type = decision.get('item_type')
            if item_type:
                if self.try_craft(item_type):
                    self.state = "crafting"
                    return
                
        elif action == 'equip':
            item_type = decision.get('item_type')
            if item_type:
                if self.try_equip(item_type):
                    self.state = "equipping"
                    return

        elif action == 'eat':
            plant_id = decision.get('plant_id')
            if plant_id and world:
                plant_obj = None
                for plant in world.plants:
                    if plant.id == plant_id and plant.is_alive:
                        plant_obj = plant
                        break

                if plant_obj:
                    if self.eating_plant is not None and self.eating_plant is not plant_obj:
                        self.stop_eating_plant(self.eating_plant)
                    self.eating_plant = plant_obj
                    self.eat_plant(plant_obj, dt)
                    self.stop()
                    self.state = "eating"
                    return

        elif action == 'move' and target is not None:
            direction = target.normalize() if target.magnitude() > 0 else Vector2(0, 0)
            self._apply_movement(direction, speed)
            if self.eating_plant is not None:
                self.stop_eating_plant(self.eating_plant)
                self.eating_plant = None
            self.state = "hunting"
            return

        elif action == 'flee' and target is not None:
            direction = target.normalize() if target.magnitude() > 0 else Vector2(0, 0)
            self._apply_movement(direction, speed)
            if self.eating_plant is not None:
                self.stop_eating_plant(self.eating_plant)
                self.eating_plant = None
            self.state = "fleeing"
            return

        elif action == 'wander':
            if self.eating_plant is not None:
                self.stop_eating_plant(self.eating_plant)
                self.eating_plant = None
            self.random_direction_timer -= dt
            if self.random_direction_timer <= 0:
                self.velocity = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * max(speed, 30)
                self.random_direction_timer = random.uniform(2, 5)
            self.state = "idle"
            return
        
        elif action == 'attack':
             target_id = decision.get('target_id')
             if target_id and world:
                 victim = self._find_entity_by_id(world, target_id)
                 if victim:
                     self._try_attack_target(world, victim)
                     return

        if self.eating_plant is not None:
            self.stop_eating_plant(self.eating_plant)
            self.eating_plant = None
        self.state = "idle"

    def behavior(self, dt: float, world=None):
        if world is None:
            return

        self.attack_timer -= dt
        sensors = self.get_sensor_data(world)

        # Пищевой цикл племени
        prev_energy = self.energy
        self._auto_eat_from_inventory(dt, world=world)
        self._share_resources_with_tribe(world)
        
        # Если ели - обновляем состояние
        if self.energy > prev_energy:
            self.state = "eating"

        # --- Pluggable brain ---
        if self.brain is not None:
            if hasattr(self.inventory, 'get_contents'):
                sensors['inventory'] = self.inventory.get_contents()
            sensors['equipped'] = self.equipped
            
            decision = self.brain.decide_action(sensors, entity=self)
            self._execute_decision(decision, dt, world)
            return

        self._legacy_heuristic_behavior(dt, world, sensors)

    def _legacy_heuristic_behavior(self, dt, world, sensors):
        """Простая эвристика для совместимости"""
        # Если уже выполняет важное действие - не переписываем
        if self.state in ("eating", "gathering", "crafting", "building", "attacking"):
            return
            
        predators = sensors['nearby_predators']
        herbivores = sensors['nearby_herbivores']
        
        # 1. Бегство
        # OPTIMIZED: Sensor data уже отсортирован по расстоянию
        closest_pred = predators[0] if predators else None
        if closest_pred and closest_pred['distance'] < 25 and self.energy > 10:
            direction = closest_pred.get('direction', Vector2(1,0))
            if isinstance(direction, Vector2):
                 self._apply_movement(direction * -1, 85)
            else:
                 self._apply_movement(Vector2(0,0), 85)
            self.state = "fleeing"
            return
            
        # 2. Охота
        if herbivores:
            # OPTIMIZED: Берём первый элемент (уже отсортирован)
            target = herbivores[0]
            if target['distance'] < self.attack_range:
                victim = self._find_entity_by_id(world, target['id'])
                if victim:
                    self._try_attack_target(world, victim)
                    return
            else:
                d = target.get('direction', Vector2(0,0))
                self.move_towards(self.pos + d * target['distance'], speed=80)
                self.state = "hunting"
                return
                
        # 3. Блуждание
        self.random_direction_timer -= dt
        if self.random_direction_timer <= 0:
            self.velocity = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * 30
            self.random_direction_timer = random.uniform(2, 5)
        self.state = "idle"
