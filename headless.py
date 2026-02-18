#!/usr/bin/env python3
"""Headless simulation application - runs without UI"""

import sys
from core.world import World
from core.config import SimulationConfig, Presets
from creatures.herbivore import Herbivore
from creatures.predator import Predator


class HeadlessSimulation:
    """Headless simulation without any UI"""
    
    def __init__(self, preset_name="balanced", duration=16.0):
        """Initialize headless simulation"""
        print("=" * 60)
        print(f"HEADLESS SIMULATION: {preset_name}")
        print("=" * 60)
        
        # Load preset
        presets = Presets()
        if preset_name == "balanced":
            self.config = presets.balanced()
        elif preset_name == "herbivore_dominated":
            self.config = presets.herbivore_dominated()
        elif preset_name == "predator_dominant":
            self.config = presets.predator_dominant()
        elif preset_name == "scarce_resources":
            self.config = presets.scarce_resources()
        else:
            self.config = SimulationConfig()
        
        print(f"World: {self.config.world.width}x{self.config.world.height}")
        print(f"Plants: {self.config.world.plant_count}")
        print(f"Herbivores: {self.config.herbivores.count}")
        print(f"Predators: {self.config.predators.count}")
        print(f"Duration: {duration}s")
        print()
        
        # Create world
        self.world = World(self.config.world.width, self.config.world.height)
        self.spawn_initial_entities()
        
        self.duration = duration
        self.frame_count = 0
        self.dt = self.config.dt
        self.update_interval = self.config.update_interval
    
    def spawn_initial_entities(self):
        """Spawn initial entities"""
        import random
        
        # Plants
        self.world.spawn_plants(
            count=self.config.world.plant_count,
            energy=self.config.world.plant_energy,
            consumption_time=self.config.world.plant_consumption_time
        )
        
        # Herbivores - random positions across the field
        for i in range(self.config.herbivores.count):
            herbivore = Herbivore(
                x=random.uniform(0, self.config.world.width),
                y=random.uniform(0, self.config.world.height)
            )
            herbivore.energy = self.config.herbivores.initial_energy
            herbivore.max_energy = self.config.herbivores.max_energy
            herbivore.health = 100.0
            herbivore.max_health = 100.0
            herbivore.vision_range = self.config.herbivores.vision_range
            herbivore.max_speed = self.config.herbivores.max_speed
            herbivore.reproduction_energy_threshold = self.config.herbivores.reproduction_energy_threshold
            self.world.add_entity(herbivore)
        
        # Predators - random positions across the field
        for i in range(self.config.predators.count):
            predator = Predator(
                x=random.uniform(0, self.config.world.width),
                y=random.uniform(0, self.config.world.height)
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
    
    def run(self):
        """Run the simulation"""
        print("Frame |    Time | Herbivores | Predators |  Plants")
        print("-" * 55)
        
        target_frames = int(self.duration / self.dt)
        
        while self.frame_count < target_frames:
            self.world.update(self.dt)
            self.frame_count += 1
            
            # Print stats every update_interval frames
            if self.frame_count % self.update_interval == 0 or self.frame_count == target_frames:
                stats = self.world.get_stats()
                print(f"{self.frame_count:5d} | {self.world.time:7.2f}s | "
                      f"{stats['herbivores_count']:10d} | "
                      f"{stats['predators_count']:9d} | {stats['plants_count']:6d}")
                
                # Stop if all creatures are extinct
                if stats['herbivores_count'] == 0 and stats['predators_count'] == 0:
                    print(f"\nAll animals extinct at frame {self.frame_count}")
                    break
        
        print(f"\nFinal | {self.world.time:7.2f}s | "
              f"{stats['herbivores_count']:10d} | "
              f"{stats['predators_count']:9d} | {stats['plants_count']:6d}")
        print()


def main():
    """Main function"""
    if len(sys.argv) > 1:
        preset = sys.argv[1]
    else:
        preset = "balanced"
    
    if len(sys.argv) > 2:
        duration = float(sys.argv[2])
    else:
        duration = 16.0
    
    sim = HeadlessSimulation(preset_name=preset, duration=duration)
    sim.run()


if __name__ == "__main__":
    main()
