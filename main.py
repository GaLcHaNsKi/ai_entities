"""Главный файл - точка входа для тестирования"""

from core.world import World
from core.config import Presets
from creatures.herbivore import Herbivore
from creatures.predator import Predator


def run_simulation(config, preset_name="custom"):
    """
    Запустить симуляцию с заданной конфигурацией
    
    Args:
        config: SimulationConfig объект
        preset_name: название предустановки для логирования
    """
    
    print(f"\n{'='*60}")
    print(f"SIMULATION: {preset_name}")
    print(f"{'='*60}")
    
    # Создаем мир
    world = World(width=config.world.width, height=config.world.height)
    print(f"World: {config.world.width}x{config.world.height}")
    
    # Добавляем растения
    world.spawn_plants(
        count=config.world.plant_count,
        energy=config.world.plant_energy,
        consumption_time=config.world.plant_consumption_time
    )
    print(f"Plants: {config.world.plant_count}")
    
    # Добавляем травоядных
    for i in range(config.herbivores.count):
        herbivore = Herbivore(
            x=50 + (i % 10) * 40,
            y=200 + (i // 10) * 40
        )
        herbivore.energy = config.herbivores.initial_energy
        herbivore.max_energy = config.herbivores.max_energy
        herbivore.health = 100.0
        herbivore.max_health = 100.0
        herbivore.vision_range = config.herbivores.vision_range
        herbivore.max_speed = config.herbivores.max_speed
        herbivore.reproduction_energy_threshold = config.herbivores.reproduction_energy_threshold
        world.add_entity(herbivore)
    print(f"Herbivores: {config.herbivores.count}")
    
    # Добавляем хищников
    for i in range(config.predators.count):
        predator = Predator(
            x=config.world.width - 100 + (i % 5) * 30,
            y=200 + (i // 5) * 40
        )
        predator.energy = config.predators.initial_energy
        predator.max_energy = config.predators.max_energy
        predator.health = 120.0
        predator.max_health = 120.0
        predator.vision_range = config.predators.vision_range
        predator.max_speed = config.predators.max_speed
        predator.attack_range = config.predators.attack_range
        predator.attack_damage = config.predators.attack_damage
        predator.attack_cooldown = config.predators.attack_cooldown
        predator.reproduction_energy_threshold = config.predators.reproduction_energy_threshold
        world.add_entity(predator)
    print(f"Predators: {config.predators.count}")
    
    # Запуск симуляции
    print(f"\nRunning for {config.max_frames} frames (~{config.max_frames * config.dt:.1f}s)...\n")
    print(f"{'Frame':>5} | {'Time':>7} | {'Herbivores':>10} | {'Predators':>9} | {'Plants':>7}")
    print("-" * 55)
    
    for frame in range(config.max_frames):
        world.update(config.dt)
        
        if frame % config.update_interval == 0:
            stats = world.get_stats()
            print(f"{frame:5d} | {world.time:7.2f}s | {stats['herbivores_count']:10d} | "
                  f"{stats['predators_count']:9d} | {stats['plants_count']:7d}")
        
        # Стоп если все вымерли
        if (stats['herbivores_count'] == 0 and stats['predators_count'] == 0):
            print(f"\nSimulation ended: All animals extinct at frame {frame}")
            break
    
    final_stats = world.get_stats()
    print(f"\n{'Final':>5} | {world.time:7.2f}s | {final_stats['herbivores_count']:10d} | "
          f"{final_stats['predators_count']:9d} | {final_stats['plants_count']:7d}")
    
    return world


def main():
    """Главная функция"""
    
    # Запуск разных предустановок
    presets_to_run = [
        ("Balanced", Presets.balanced()),
        ("Herbivore Dominated", Presets.herbivore_dominated()),
        ("Predator Dominant", Presets.predator_dominant()),
        ("Scarce Resources", Presets.scarce_resources()),
    ]
    
    for preset_name, config in presets_to_run:
        run_simulation(config, preset_name)
    
    print(f"\n{'='*60}")
    print("All simulations completed!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
