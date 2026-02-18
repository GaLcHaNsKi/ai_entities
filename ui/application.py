"""Главное приложение с Tkinter UI и Pygame визуализацией"""

import sys
import os
import threading
import time
from core.world import World
from core.config import SimulationConfig
from creatures.herbivore import Herbivore
from creatures.predator import Predator
from creatures.smart import SmartCreature
from ai.brain import create_brain
from ui.settings import SettingsWindow
from ui.pygame_renderer import PygameRenderer


class SimulationApp:
    """Главное приложение"""
    
    def __init__(self):
        """Инициализация приложения"""
        print("Starting AI Entities - Ecosystem Simulation")
        
        # Загружаем настройки через Tkinter UI
        settings_window = SettingsWindow()
        self.config = settings_window.get_config()
        
        if self.config is None:
            print("Simulation cancelled")
            sys.exit(0)
        
        print(f"Loaded config: {self.config.world.width}x{self.config.world.height}")
        print(f"Herbivores: {self.config.herbivores.count}")
        print(f"Predators: {self.config.predators.count}")
        print(f"Smarts: {self.config.smarts.count}")
        print(f"Plants: {self.config.world.plant_count}")
        print(
            f"Resources (T/S/Cu/Fe): {self.config.world.tree_count}/"
            f"{self.config.world.stone_count}/"
            f"{self.config.world.copper_count}/"
            f"{self.config.world.iron_count}"
        )
        
        # Создаем мир
        self.world = World(self.config.world.width, self.config.world.height)
        self.spawn_initial_entities()
        
        # Создаем Pygame рендер (полноэкранный -> оконный для стабильности)
        self.renderer = PygameRenderer(fullscreen=False)
        self.renderer.set_world_size(self.config.world.width, self.config.world.height)
        
        # Параметры симуляции
        self.paused = False
        self.speed_multiplier = 1.0  # 1x скорость
        self.running = True
        self.frame_skip = 1  # рендер каждый N фрейм
    
    def spawn_initial_entities(self):
        """Создать начальные существа и растения"""
        import random
        
        print("\nSpawning entities...")
        
        # Добавляем растения
        self.world.spawn_plants(
            count=self.config.world.plant_count,
            energy=self.config.world.plant_energy,
            consumption_time=self.config.world.plant_consumption_time
        )
        print(f"  Plants: {self.config.world.plant_count}")

        # Добавляем статические ресурсы
        self.world.spawn_resources(
            tree_count=self.config.world.tree_count,
            stone_count=self.config.world.stone_count,
            copper_count=self.config.world.copper_count,
            iron_count=self.config.world.iron_count,
        )
        print(
            f"  Resources (T/S/Cu/Fe): {self.config.world.tree_count}/"
            f"{self.config.world.stone_count}/"
            f"{self.config.world.copper_count}/"
            f"{self.config.world.iron_count}"
        )
        
        # Добавляем травоядных - случайные позиции по всему полю
        for i in range(self.config.herbivores.count):
            brain = create_brain(
                self.config.herbivores.brain_type,
                "herbivore"
            )
            herbivore = Herbivore(
                x=random.uniform(0, self.config.world.width),
                y=random.uniform(0, self.config.world.height),
                brain=brain,
            )
            herbivore.energy = self.config.herbivores.initial_energy
            herbivore.max_energy = self.config.herbivores.max_energy
            herbivore.health = 100.0
            herbivore.max_health = 100.0
            herbivore.vision_range = self.config.herbivores.vision_range
            herbivore.max_speed = self.config.herbivores.max_speed
            herbivore.reproduction_energy_threshold = self.config.herbivores.reproduction_energy_threshold
            self.world.add_entity(herbivore)
        print(f"  Herbivores: {self.config.herbivores.count} (brain={self.config.herbivores.brain_type})")
        
        # Добавляем хищников - случайные позиции по всему полю
        for i in range(self.config.predators.count):
            brain = create_brain(
                self.config.predators.brain_type,
                "predator"
            )
            predator = Predator(
                x=random.uniform(0, self.config.world.width),
                y=random.uniform(0, self.config.world.height),
                brain=brain,
            )
            predator.energy = self.config.predators.initial_energy
            predator.max_energy = self.config.predators.max_energy
            predator.health = 120.0
            predator.max_health = 120.0
            predator.vision_range = self.config.predators.vision_range
            predator.max_speed = self.config.predators.max_speed
            predator.attack_range = self.config.predators.attack_range
            predator.attack_damage = self.config.predators.attack_damage
            predator.attack_cooldown = self.config.predators.attack_cooldown
            predator.reproduction_energy_threshold = self.config.predators.reproduction_energy_threshold
            self.world.add_entity(predator)
        print(f"  Predators: {self.config.predators.count} (brain={self.config.predators.brain_type})")

        # Добавляем разумных существ
        smart_total = self.config.smarts.count
        min_tribe_size = 3
        max_tribe_size = 7
        tribe_id = 1
        spawned = 0

        while spawned < smart_total:
            tribe_size = random.randint(min_tribe_size, max_tribe_size)
            tribe_size = min(tribe_size, smart_total - spawned)

            # Центр спавна племени (одна точка)
            spawn_x = random.uniform(0, self.config.world.width)
            spawn_y = random.uniform(0, self.config.world.height)

            for _ in range(tribe_size):
                brain = create_brain(
                    self.config.smarts.brain_type,
                    "smart"
                )
                # Спавн кучкой с минимальным разбросом
                smart = SmartCreature(
                    x=spawn_x + random.uniform(-8, 8),
                    y=spawn_y + random.uniform(-8, 8),
                    brain=brain,
                )
                smart.tribe_id = tribe_id
                smart.energy = self.config.smarts.initial_energy
                smart.max_energy = self.config.smarts.max_energy
                smart.health = 100.0
                smart.max_health = 100.0
                smart.vision_range = self.config.smarts.vision_range
                smart.max_speed = self.config.smarts.max_speed
                smart.attack_range = self.config.smarts.attack_range
                smart.attack_damage = self.config.smarts.attack_damage
                smart.attack_cooldown = self.config.smarts.attack_cooldown
                smart.reproduction_energy_threshold = self.config.smarts.reproduction_energy_threshold
                self.world.add_entity(smart)
                spawned += 1

            tribe_id += 1

        print(f"  Smarts: {self.config.smarts.count} (brain={self.config.smarts.brain_type}, tribes={tribe_id - 1})")
        print(f"\nTotal entities: {len(self.world.entities)}\n")
    
    def run(self):
        """Запустить симуляцию"""
        print("Starting simulation... (Press SPACE to pause, Q to quit)")
        print("=" * 60)
        
        frame_count = 0
        render_frame_count = 0
        last_log_time = time.time()
        
        # Принудительно "прокачиваем" события перед стартом, чтобы окно ожило
        try:
            import pygame
            pygame.event.pump()
        except:
            pass
            
        try:
            while self.running:
                # Обработаем события
                events = self.renderer.handle_events(world=self.world)
                
                if events['quit']:
                    print("\nSimulation stopped by user (window closed or Q pressed)")
                    break  # Выходим из цикла вместо self.running = False
                
                if events['pause']:
                    self.paused = not self.paused
                    print(f"Simulation {'paused' if self.paused else 'resumed'}")
                
                if events['speed_up']:
                    self.speed_multiplier = min(4.0, self.speed_multiplier + 0.5)
                    print(f"Speed: {self.speed_multiplier:.1f}x")
                
                if events['speed_down']:
                    self.speed_multiplier = max(0.1, self.speed_multiplier - 0.5)
                    print(f"Speed: {self.speed_multiplier:.1f}x")
                
                if events['reset']:
                    print("Resetting simulation...")
                    self.world = World(self.config.world.width, self.config.world.height)
                    self.spawn_initial_entities()
                    self.paused = False
                
                # Обновляем симуляцию
                if not self.paused:
                    for _ in range(int(self.speed_multiplier)):
                        self.world.update(self.config.dt)
                        frame_count += 1
                
                # Рендер каждый frame_skip кадр
                render_frame_count += 1
                if render_frame_count >= self.frame_skip:
                    # Если выбрано существо - центрируем на нем
                    if self.renderer.selected_entity and self.renderer.selected_entity.is_alive:
                        self.renderer.center_on_cluster((
                            self.renderer.selected_entity.pos.x,
                            self.renderer.selected_entity.pos.y
                        ))
                    
                    self.renderer.render(
                        self.world,
                        simulation_time=self.world.time,
                        paused=self.paused,
                        speed=self.speed_multiplier
                    )
                    render_frame_count = 0
                
                # FPS контроль (30 FPS для рендера)
                self.renderer.set_fps(30)
                
                # Выводим статистику каждые N фреймов
                if frame_count % (self.config.update_interval * int(self.speed_multiplier)) == 0 and frame_count > 0:
                    stats = self.world.get_stats()
                    print(f"Frame {frame_count:5d} | Time: {self.world.time:7.2f}s | "
                          f"Herbivores: {stats['herbivores_count']:3d} | "
                          f"Predators: {stats['predators_count']:2d} | "
                          f"Smarts: {stats.get('smarts_count', 0):2d} | "
                          f"Tribes: {stats.get('smart_tribes_count', 0):2d} | "
                          f"Plants: {stats['plants_count']:3d} | "
                          f"Res: {stats.get('resources_count', 0):3d}")
                
                # Стоп если все вымерли
                stats = self.world.get_stats()
                if stats['herbivores_count'] == 0 and stats['predators_count'] == 0 and stats.get('smarts_count', 0) == 0:
                    print(f"\n⚠️  Simulation ended: All animals extinct at frame {frame_count}")
                    print("(Closing window to return to menu)")
                    break  # Аккуратно выходим из цикла
        
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Очистка"""
        print("\nClosing simulation...")
        self.renderer.quit()


def main():
    """Главная функция"""
    app = SimulationApp()
    app.run()


if __name__ == "__main__":
    main()
