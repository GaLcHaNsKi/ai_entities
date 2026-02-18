"""Система статистики и логирования симуляции"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class FrameStats:
    """Статистика за один кадр"""
    frame: int
    time: float
    herbivore_count: int
    predator_count: int
    plant_count: int
    total_herbivore_energy: float
    total_predator_energy: float
    avg_herbivore_energy: float
    avg_predator_energy: float


class StatisticsCollector:
    """Собирает и анализирует статистику симуляции"""
    
    def __init__(self):
        self.frames: List[FrameStats] = []
        self.is_recording = False
    
    def start_recording(self):
        """Начать запись статистики"""
        self.frames = []
        self.is_recording = True
    
    def stop_recording(self):
        """Остановить запись"""
        self.is_recording = False
    
    def collect_frame(self, world):
        """Собрать статистику за текущий кадр"""
        if not self.is_recording:
            return
        
        # Подсчитываем энергию
        total_herbivore_energy = 0.0
        total_predator_energy = 0.0
        herbivore_count = 0
        predator_count = 0
        
        for entity in world.entities:
            if entity.entity_type == "herbivore":
                herbivore_count += 1
                total_herbivore_energy += entity.energy
            elif entity.entity_type == "predator":
                predator_count += 1
                total_predator_energy += entity.energy
        
        avg_herbivore_energy = total_herbivore_energy / herbivore_count if herbivore_count > 0 else 0.0
        avg_predator_energy = total_predator_energy / predator_count if predator_count > 0 else 0.0
        
        stats = FrameStats(
            frame=world.frame,
            time=world.time,
            herbivore_count=herbivore_count,
            predator_count=predator_count,
            plant_count=len([p for p in world.plants if p.is_alive]),
            total_herbivore_energy=total_herbivore_energy,
            total_predator_energy=total_predator_energy,
            avg_herbivore_energy=avg_herbivore_energy,
            avg_predator_energy=avg_predator_energy
        )
        
        self.frames.append(stats)
    
    def get_stats(self, start_frame=None, end_frame=None) -> List[FrameStats]:
        """Получить статистику за диапазон кадров"""
        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = len(self.frames)
        
        return self.frames[start_frame:end_frame]
    
    def get_summary(self) -> Dict[str, Any]:
        """Получить сводку по всей симуляции"""
        if not self.frames:
            return {}
        
        first_frame = self.frames[0]
        last_frame = self.frames[-1]
        
        # Найти макимум популяций
        max_herbivores = max(f.herbivore_count for f in self.frames)
        max_predators = max(f.predator_count for f in self.frames)
        
        # Найти среднее
        avg_herbivores = sum(f.herbivore_count for f in self.frames) / len(self.frames)
        avg_predators = sum(f.predator_count for f in self.frames) / len(self.frames)
        
        return {
            'total_duration': last_frame.time,
            'total_frames': len(self.frames),
            'initial_herbivores': first_frame.herbivore_count,
            'initial_predators': first_frame.predator_count,
            'final_herbivores': last_frame.herbivore_count,
            'final_predators': last_frame.predator_count,
            'max_herbivores': max_herbivores,
            'max_predators': max_predators,
            'avg_herbivores': avg_herbivores,
            'avg_predators': avg_predators,
        }
    
    def save_to_json(self, filepath: str):
        """Сохранить статистику в JSON"""
        data = {
            'frames': [asdict(f) for f in self.frames],
            'summary': self.get_summary()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_json(self, filepath: str):
        """Загрузить статистику из JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.frames = [FrameStats(**frame_data) for frame_data in data['frames']]
