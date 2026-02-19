"""Основной класс мира - управляет всей симуляцией"""

import random
import math
from collections import defaultdict
from core.physics import Vector2
from core.resource import Plant, ResourceNode
from core.building import Building, BuildingType


class SpatialGrid:
    """
    Spatial hashing grid для быстрого поиска объектов по позиции.
    Делит мир на ячейки (cells) и хранит объекты в клеточной сетке.
    Поиск в радиусе от O(N) → O(1) в среднем случае.
    """
    
    def __init__(self, world_width: float, world_height: float, cell_size: float = 100.0):
        self.world_width = world_width
        self.world_height = world_height
        self.cell_size = cell_size
        
        # Размер сетки в ячейках
        self.grid_width = int(math.ceil(world_width / cell_size))
        self.grid_height = int(math.ceil(world_height / cell_size))
        
        # Сетка: (grid_x, grid_y) → [объекты]
        self.plants_grid = defaultdict(list)
        self.entities_grid = defaultdict(list)
        
        # ОПТИМИЗАЦИЯ: Lazy updates - кешируем старые позиции для batch обновления
        self.entity_cell_cache = {}  # entity.id → old_cell
        self.entities_to_update = set()  # entity.id список для обновления
    
    def _get_cell(self, pos: Vector2) -> tuple:
        """Получить координаты ячейки для позиции"""
        gx = int(pos.x // self.cell_size)
        gy = int(pos.y // self.cell_size)
        # Ограничиваем границами сетки
        gx = max(0, min(gx, self.grid_width - 1))
        gy = max(0, min(gy, self.grid_height - 1))
        return (gx, gy)
    
    def _get_nearby_cells(self, pos: Vector2, radius: float) -> list:
        """Получить все ячейки в радиусе от позиции"""
        cells = []
        cell_radius = int(math.ceil(radius / self.cell_size))
        gx, gy = self._get_cell(pos)
        
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    cells.append((nx, ny))
        return cells
    
    def add_plant(self, plant):
        """Добавить растение в сетку"""
        cell = self._get_cell(plant.pos)
        self.plants_grid[cell].append(plant)
    
    def add_entity(self, entity):
        """Добавить сущность в сетку"""
        cell = self._get_cell(entity.pos)
        self.entities_grid[cell].append(entity)
        self.entity_cell_cache[entity.id] = cell
    
    def mark_entity_moved(self, entity):
        """Отметить сущность что она движется (для lazy update)"""
        self.entities_to_update.add(entity.id)
    
    def update_entity_positions(self, entities: list):
        """
        Обновить позиции только тех сущностей которые движутся (lazy update).
        Вместо пересчета всей сетки, обновляем только отмеченные.
        """
        for entity in entities:
            if entity.id not in self.entities_to_update:
                continue
            if not entity.is_alive:
                continue
            
            new_cell = self._get_cell(entity.pos)
            old_cell = self.entity_cell_cache.get(entity.id)
            
            if old_cell != new_cell:
                # Сущность переместилась в другую ячейку
                if old_cell and entity in self.entities_grid[old_cell]:
                    self.entities_grid[old_cell].remove(entity)
                self.entities_grid[new_cell].append(entity)
                self.entity_cell_cache[entity.id] = new_cell
        
        # Очищаем список на обновление для следующего frame
        self.entities_to_update.clear()
    
    def clear(self):
        """Очистить сетку и пересчитать с нуля"""
        self.plants_grid.clear()
        self.entities_grid.clear()
        self.entity_cell_cache.clear()
        self.entities_to_update.clear()
    
    def rebuild(self, plants: list, entities: list):
        """Пересчитать сетку с нуля (вызывать после больших изменений)"""
        self.clear()
        for plant in plants:
            if plant.is_alive:
                self.add_plant(plant)
        for entity in entities:
            if entity.is_alive:
                self.add_entity(entity)
    
    def rebuild_plants(self, plants: list):
        """Пересчитать только plants grid (они не двигаются часто)"""
        self.plants_grid.clear()
        for plant in plants:
            if plant.is_alive:
                self.add_plant(plant)
    
    def get_plants_in_radius(self, pos: Vector2, radius: float) -> list:
        """Получить растения в радиусе (отсортировано по расстоянию)"""
        nearby_cells = self._get_nearby_cells(pos, radius)
        nearby = []
        radius_sq = radius * radius
        
        for cell in nearby_cells:
            for plant in self.plants_grid[cell]:
                if not plant.is_alive:
                    continue
                dx = plant.pos.x - pos.x
                dy = plant.pos.y - pos.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= radius_sq:
                    dist = dist_sq ** 0.5
                    nearby.append((plant, dist))
        
        return sorted(nearby, key=lambda x: x[1])
    
    def get_entities_in_radius(self, pos: Vector2, radius: float, exclude_id=None) -> list:
        """Получить сущности в радиусе (отсортировано по расстоянию)"""
        nearby_cells = self._get_nearby_cells(pos, radius)
        nearby = []
        radius_sq = radius * radius
        
        for cell in nearby_cells:
            for entity in self.entities_grid[cell]:
                if exclude_id and entity.id == exclude_id:
                    continue
                if not entity.is_alive:
                    continue
                dx = entity.pos.x - pos.x
                dy = entity.pos.y - pos.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= radius_sq:
                    dist = dist_sq ** 0.5
                    nearby.append((entity, dist))
        
        return sorted(nearby, key=lambda x: x[1])


class World:
    """
    Главный класс симуляции
    Содержит все существа, растения, управляет обновлением
    """
    
    def __init__(self, width: float = 1200.0, height: float = 1200.0):
        self.width = width
        self.height = height
        
        self.entities = []  # все существа
        self.plants = []    # все растения
        self.resources = []  # статические ресурсы (деревья, камни, руда)
        self.buildings = [] # player built structures
        self.smart_tribes = {}  # tribe_id -> [SmartCreature, ...]
        
        # Spatial hashing grid для быстрого поиска объектов
        self.spatial_grid = SpatialGrid(width, height, cell_size=100.0)
        self.grid_rebuild_counter = 0  # Пересчитываем grid каждые N кадров
        
        self.time = 0.0  # общее прошедшее время симуляции
        self.frame = 0   # номер кадра
        
        self.stats = {
            'herbivores_count': 0,
            'predators_count': 0,
            'smarts_count': 0,
            'smart_tribes_count': 0,
            'plants_count': 0,
            'trees_count': 0,
            'stones_count': 0,
            'copper_count': 0,
            'iron_count': 0,
            'resources_count': 0,
        }
    
    def add_entity(self, entity):
        """Добавить существо в мир"""
        self.entities.append(entity)
    
    def remove_entity(self, entity):
        """Удалить существо из мира"""
        if entity in self.entities:
            self.entities.remove(entity)
    
    def add_plant(self, x: float, y: float, energy: float = 100.0, consumption_time: float = 2.0):
        """Добавить растение на карту"""
        plant = Plant(x, y, energy, consumption_time)
        self.plants.append(plant)
        return plant

    def add_resource(self, x: float, y: float, resource_type: str, amount: float = 100.0):
        """Добавить статический ресурс на карту"""
        node = ResourceNode(x, y, resource_type, amount)
        self.resources.append(node)
        return node
    
    def spawn_plants(self, count: int, energy: float = 100.0, consumption_time: float = 2.0):
        """Создать растения в случайных местах"""
        self.plant_respawn_config = {
            'count': count,
            'energy': energy,
            'consumption_time': consumption_time,
            'respawn_time': 5.0,  # размножаться каждые 5 секунд
            'last_respawn': 0.0
        }
        for _ in range(count):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            self.add_plant(x, y, energy, consumption_time)

    def spawn_resources(self, tree_count: int = 0, stone_count: int = 0,
                        copper_count: int = 0, iron_count: int = 0):
        """Создать статические ресурсы в случайных местах."""
        for _ in range(max(0, tree_count)):
            self.add_resource(
                random.uniform(0, self.width),
                random.uniform(0, self.height),
                "tree",
                amount=120.0,
            )

        for _ in range(max(0, stone_count)):
            self.add_resource(
                random.uniform(0, self.width),
                random.uniform(0, self.height),
                "stone",
                amount=180.0,
            )

        # Медь встречается чаще железа
        for _ in range(max(0, copper_count)):
            self.add_resource(
                random.uniform(0, self.width),
                random.uniform(0, self.height),
                "copper",
                amount=90.0,
            )

        for _ in range(max(0, iron_count)):
            self.add_resource(
                random.uniform(0, self.width),
                random.uniform(0, self.height),
                "iron",
                amount=110.0,
            )
    
    def clamp_position(self, pos: Vector2) -> Vector2:
        """Ограничить позицию границами мира"""
        x = max(0, min(self.width, pos.x))
        y = max(0, min(self.height, pos.y))
        return Vector2(x, y)

    def add_building(self, b_type: BuildingType, x: float, y: float, owner_id: int):
        """Place a building in the world"""
        # Basic collision check with other buildings
        for b in self.buildings:
            if (b.x - x)**2 + (b.y - y)**2 < (b.radius + 5)**2: # Simple radius check
                return None
        
        b = Building(b_type, x, y, owner_id)
        self.buildings.append(b)
        return b
    
    def update(self, dt: float):
        """
        Основной цикл обновления мира
        Вызывается каждый фрейм
        """
        self.time += dt
        self.frame += 1
        
        # 0. Update Buildings
        dead_buildings = []
        for b in self.buildings:
            if b.is_destroyed():
                dead_buildings.append(b)
                continue
            
            b.timer += dt
            
            # House: Heal owner if nearby
            if b.type == BuildingType.HOUSE:
                if b.timer >= 1.0: # Every second
                    b.timer = 0
                    for entity in self.entities:
                        if entity.id == b.owner_id and entity.is_alive:
                            dist_sq = (entity.position.x - b.x)**2 + (entity.position.y - b.y)**2
                            if dist_sq < b.radius**2:
                                entity.health = min(entity.max_health, entity.health + 5.0)

            # Farm: Spawn food nearby
            elif b.type == BuildingType.FARM_PLOT:
                if b.timer >= 10.0: # Every 10 seconds
                    b.timer = 0
                    # Spawn a plant nearby
                    angle = random.uniform(0, 6.28)
                    dist = random.uniform(2, b.radius)
                    px = b.x + dist * math.cos(angle)
                    py = b.y + dist * math.sin(angle)
                    
                    # Keep in bounds
                    px = max(0, min(self.width, px))
                    py = max(0, min(self.height, py))
                    
                    # Add plant
                    self.add_plant(px, py, energy=30.0)

        for b in dead_buildings:
            if b in self.buildings:
                self.buildings.remove(b)
        
        # 1. Обновляем растения
        dead_plants = []
        for plant in self.plants:
            if not plant.is_alive:
                dead_plants.append(plant)
                continue
            
            # Растение распределяет энергию между едящими
            energy_given = plant.update(dt)
            
            # Даем энергию существам
            for entity_id, energy in energy_given.items():
                for entity in self.entities:
                    if entity.id == entity_id and entity.is_alive:
                        entity.gain_energy(energy)
        
        # Обновляем статические ресурсы (добыча)
        dead_resources = []
        for res in self.resources:
            if not res.is_alive:
                dead_resources.append(res)
                continue
                
            items_given = res.update(dt)
            if items_given:
                # Импортируем типы здесь, чтобы избежать круговых ссылок на уровне модуля
                from core.items import ItemType
                
                type_map = {
                    "tree": ItemType.WOOD,
                    "stone": ItemType.STONE,
                    "copper": ItemType.COPPER_ORE,
                    "iron": ItemType.IRON_ORE
                }
                
                item_type = type_map.get(res.resource_type)
                if item_type:
                    for entity_id, count in items_given.items():
                        for entity in self.entities:
                            if entity.id == entity_id and entity.is_alive:
                                if hasattr(entity, 'inventory'):
                                    entity.inventory.add_item(item_type, count)
        
        # Удаляем мертвые ресурсы
        for res in dead_resources:
            if res in self.resources:
                self.resources.remove(res)

        # Удаляем мертвые растения
        for plant in dead_plants:
            if plant in self.plants:
                self.plants.remove(plant)
        
        # Возрождаем новые растения (если конфигурирован)
        if hasattr(self, 'plant_respawn_config'):
            self.plant_respawn_config['last_respawn'] += dt
            if self.plant_respawn_config['last_respawn'] >= self.plant_respawn_config['respawn_time']:
                # Добавляем новые растения
                needed = self.plant_respawn_config['count'] - len(self.plants)
                for _ in range(needed):
                    x = random.uniform(0, self.width)
                    y = random.uniform(0, self.height)
                    self.add_plant(
                        x, y,
                        self.plant_respawn_config['energy'],
                        self.plant_respawn_config['consumption_time']
                    )
                self.plant_respawn_config['last_respawn'] = 0.0
        
        # 2. Обновляем существ
        dead_entities = []
        
        # Iterate over a COPY of the list to avoid issues with adding/removing entities during iteration
        for entity in list(self.entities):
            if not entity.is_alive:
                dead_entities.append(entity)
                continue
            
            # ОПТИМИЗАЦИЯ: Отмечаем что entity движется (для lazy grid update)
            self.spatial_grid.mark_entity_moved(entity)
            
            # Поведение (ИИ решает что делать)
            entity.behavior(dt, self)
            
            # Физика (движение, расход энергии)
            entity.update(dt, self)
            
            # Ограничиваем позицию границами мира
            entity.pos = self.clamp_position(entity.pos)
        
        # Удаляем мертвые существа
        for entity in dead_entities:
            if entity in self.entities:
                self.entities.remove(entity)
        
        # 3. ОПТИМИЗАЦИЯ: Обновляем spatial grid используя lazy update вместо полного rebuild
        # Обновляем позиции только тех entities которые реально движутся
        self.spatial_grid.update_entity_positions(self.entities)
        
        # Пересчитываем plants grid (они не двигаются, но могут удаляться)
        if self.frame % 5 == 0:  # Пересчитываем plants grid каждые 5 фреймов
            self.spatial_grid.rebuild_plants(self.plants)
        
        # 4. Обновляем статистику
        self.update_stats()
    
    def get_plants_in_radius(self, pos, radius: float):
        """
        Получить растения в радиусе (использует spatial grid для быстрого поиска).
        Сортировано по расстоянию (ближайшие в начале).
        O(1) вместо O(N) с spatial hashing!
        """
        return self.spatial_grid.get_plants_in_radius(pos, radius)
    
    def get_entities_in_radius(self, pos, radius: float, exclude_id=None):
        """
        Получить сущности в радиусе (использует spatial grid для быстрого поиска).
        Сортировано по расстоянию.
        O(1) вместо O(N) с spatial hashing!
        """
        return self.spatial_grid.get_entities_in_radius(pos, radius, exclude_id=exclude_id)
    
    def update_stats(self):
        """Обновить статистику (оптимизированная версия)"""
        # Сбрасываем счетчики
        self.stats['herbivores_count'] = 0
        self.stats['predators_count'] = 0
        self.stats['smarts_count'] = 0
        self.smart_tribes = {}
        
        # Один проход по сущностям
        for entity in self.entities:
            if not entity.is_alive:
                continue
            
            etype = entity.entity_type
            if etype == "herbivore":
                self.stats['herbivores_count'] += 1
            elif etype == "predator":
                self.stats['predators_count'] += 1
            elif etype == "smart":
                self.stats['smarts_count'] += 1
                tribe_id = getattr(entity, 'tribe_id', 0)
                if tribe_id not in self.smart_tribes:
                    self.smart_tribes[tribe_id] = []
                self.smart_tribes[tribe_id].append(entity)
        
        self.stats['smart_tribes_count'] = len(self.smart_tribes)

        # Растения просто берем длину списка, так как мертвые удаляются в update()
        self.stats['plants_count'] = len(self.plants)
        
        # Ресурсы - аналогично один проход
        self.stats['trees_count'] = 0
        self.stats['stones_count'] = 0
        self.stats['copper_count'] = 0
        self.stats['iron_count'] = 0
        
        for r in self.resources:
            if not r.is_alive: 
                continue
            rt = r.resource_type
            if rt == "tree": self.stats['trees_count'] += 1
            elif rt == "stone": self.stats['stones_count'] += 1
            elif rt == "copper": self.stats['copper_count'] += 1
            elif rt == "iron": self.stats['iron_count'] += 1
            
        self.stats['resources_count'] = len(self.resources)
    
    def get_stats(self) -> dict:
        """Получить текущую статистику"""
        return self.stats.copy()
    
    def __repr__(self):
        return f"World({self.width}x{self.height}, entities={len(self.entities)}, plants={len(self.plants)}, resources={len(self.resources)})"
