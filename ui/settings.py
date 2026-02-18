"""Tkinter интерфейс для настроек симуляции"""

import tkinter as tk
from tkinter import ttk, messagebox
from core.config import SimulationConfig, Presets


class SettingsWindow:
    """Окно с настройками симуляции"""
    
    def __init__(self, parent=None):
        """Инициализация окна настроек"""
        self.root = tk.Tk() if parent is None else tk.Toplevel(parent)
        self.root.title("AI Entities - Settings")
        self.root.geometry("475x1050")
        self.root.resizable(True, True)
        
        # Стиль
        style = ttk.Style()
        style.theme_use('clam')
        
        # Конфигурация
        self.config = SimulationConfig()
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Результат
        self.result = None
    
    def create_widgets(self):
        """Создать элементы интерфейса"""
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas для прокрутки
        canvas = tk.Canvas(main_container, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Прокрутка колесом мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Заголовок
        title = ttk.Label(scrollable_frame, text="Simulation Settings", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Предустановки
        self.create_presets_section(scrollable_frame)
        
        # Разделитель
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Параметры мира
        self.create_world_section(scrollable_frame)
        
        # Параметры травоядных
        self.create_herbivore_section(scrollable_frame)
        
        # Параметры хищников
        self.create_predator_section(scrollable_frame)

        # Параметры разумных существ
        self.create_smart_section(scrollable_frame)
        
        # Кнопки внизу
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=20, padx=10)
        
        start_btn = ttk.Button(button_frame, text="▶ Start Simulation", command=self.start_simulation)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = ttk.Button(button_frame, text="↺ Reset", command=self.reset_config)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        quit_btn = ttk.Button(button_frame, text="✕ Quit", command=self.root.quit)
        quit_btn.pack(side=tk.LEFT, padx=5)
    
    def create_presets_section(self, parent):
        """Создать секцию предустановок"""
        frame = ttk.LabelFrame(parent, text="Presets", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        presets = [
            ("Balanced", Presets.balanced),
            ("Herbivore Dominated", Presets.herbivore_dominated),
            ("Predator Dominant", Presets.predator_dominant),
            ("Scarce Resources", Presets.scarce_resources),
        ]
        
        for name, preset_func in presets:
            btn = ttk.Button(
                frame,
                text=name,
                command=lambda pf=preset_func: self.load_preset(pf)
            )
            btn.pack(fill=tk.X, pady=3)
    
    def create_world_section(self, parent):
        """Создать секцию параметров мира"""
        frame = ttk.LabelFrame(parent, text="World", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # Размер мира - целые числа
        self.width_var = self.create_slider(frame, "World Width", 1000, 3000, self.config.world.width, is_int=True)
        self.height_var = self.create_slider(frame, "World Height", 1000, 3000, self.config.world.height, is_int=True)
        
        # Растения
        self.plant_count_var = self.create_slider(frame, "Plant Count", 10, 500, self.config.world.plant_count, is_int=True)
        self.plant_energy_var = self.create_slider(frame, "Plant Energy", 50, 200, self.config.world.plant_energy)

        # Статические ресурсы
        self.tree_count_var = self.create_slider(frame, "Tree Count", 0, 300, self.config.world.tree_count, is_int=True)
        self.stone_count_var = self.create_slider(frame, "Stone Count", 0, 300, self.config.world.stone_count, is_int=True)
        self.copper_count_var = self.create_slider(frame, "Copper Count", 0, 200, self.config.world.copper_count, is_int=True)
        self.iron_count_var = self.create_slider(frame, "Iron Count", 0, 200, self.config.world.iron_count, is_int=True)
    
    def create_herbivore_section(self, parent):
        """Создать секцию параметров травоядных"""
        frame = ttk.LabelFrame(parent, text="Herbivores", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        self.herbivore_count_var = self.create_slider(frame, "Count", 0, 100, self.config.herbivores.count)
        self.herbivore_max_energy_var = self.create_slider(frame, "Max Energy", 50, 200, self.config.herbivores.max_energy)
        self.herbivore_init_energy_var = self.create_slider(frame, "Initial Energy", 20, 150, self.config.herbivores.initial_energy)
        self.herbivore_vision_var = self.create_slider(frame, "Vision Range", 20, 150, self.config.herbivores.vision_range)
        
        # Brain type
        self.herbivore_brain_var = self.create_brain_selector(frame, "Brain Type", self.config.herbivores.brain_type)
    
    def create_predator_section(self, parent):
        """Создать секцию параметров хищников"""
        frame = ttk.LabelFrame(parent, text="Predators", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        self.predator_count_var = self.create_slider(frame, "Count", 0, 50, self.config.predators.count)
        self.predator_max_energy_var = self.create_slider(frame, "Max Energy", 100, 250, self.config.predators.max_energy)
        self.predator_init_energy_var = self.create_slider(frame, "Initial Energy", 50, 200, self.config.predators.initial_energy)
        self.predator_vision_var = self.create_slider(frame, "Vision Range", 50, 200, self.config.predators.vision_range)
        self.predator_damage_var = self.create_slider(frame, "Attack Damage", 10, 80, self.config.predators.attack_damage)
        
        # Brain type
        self.predator_brain_var = self.create_brain_selector(frame, "Brain Type", self.config.predators.brain_type)

    def create_smart_section(self, parent):
        """Создать секцию параметров разумных существ"""
        frame = ttk.LabelFrame(parent, text="Smart Creatures", padding=10)
        frame.pack(fill=tk.X, pady=5)

        self.smart_count_var = self.create_slider(frame, "Count", 0, 80, self.config.smarts.count, is_int=True)
        self.smart_max_energy_var = self.create_slider(frame, "Max Energy", 60, 220, self.config.smarts.max_energy)
        self.smart_init_energy_var = self.create_slider(frame, "Initial Energy", 20, 180, self.config.smarts.initial_energy)
        self.smart_vision_var = self.create_slider(frame, "Vision Range", 30, 180, self.config.smarts.vision_range)
        self.smart_damage_var = self.create_slider(frame, "Attack Damage", 5, 50, self.config.smarts.attack_damage)

        self.smart_brain_var = self.create_brain_selector(frame, "Brain Type", self.config.smarts.brain_type)
    
    def create_brain_selector(self, parent, label, default_val):
        """Создать выпадающий список выбора мозга."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        lbl = ttk.Label(frame, text=label, width=20)
        lbl.pack(side=tk.LEFT)
        
        var = tk.StringVar(value=default_val)
        combo = ttk.Combobox(frame, textvariable=var, values=["heuristic", "rl"], state="readonly", width=12)
        combo.pack(side=tk.LEFT, padx=5)
        
        return var
    
    def create_slider(self, parent, label, min_val, max_val, default_val, is_int=False):
        """Создать слайдер с меткой"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        lbl = ttk.Label(frame, text=label, width=20)
        lbl.pack(side=tk.LEFT)
        
        # Использовать IntVar для целых чисел, иначе DoubleVar
        VarClass = tk.IntVar if is_int else tk.DoubleVar
        var = VarClass(value=int(default_val) if is_int else float(default_val))
        slider = ttk.Scale(frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL, variable=var)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        value_lbl = ttk.Label(frame, text=f"{default_val:.0f}", width=5)
        value_lbl.pack(side=tk.RIGHT)
        
        # Обновляем значение при движении слайдера
        def update_label(val):
            value_lbl.config(text=f"{float(val):.0f}")
        
        slider.config(command=update_label)
        
        # Сохраняем ссылку
        return var
    
    def load_preset(self, preset_func):
        """Загрузить предустановку"""
        self.config = preset_func()
        # Обновляем все слайдеры (при необходимости)
        messagebox.showinfo("Preset Loaded", "Preset loaded successfully!")
    
    def reset_config(self):
        """Сброс конфига"""
        self.config = SimulationConfig()
        messagebox.showinfo("Reset", "Settings reset to defaults!")
    
    def start_simulation(self):
        """Начать симуляцию"""
        # Собираем параметры из UI
        width = self.width_var.get()
        height = self.height_var.get()
        
        self.config.world.width = float(width)
        self.config.world.height = float(height)
        self.config.world.plant_count = int(self.plant_count_var.get())
        self.config.world.plant_energy = self.plant_energy_var.get()
        self.config.world.tree_count = int(self.tree_count_var.get())
        self.config.world.stone_count = int(self.stone_count_var.get())
        self.config.world.copper_count = int(self.copper_count_var.get())
        self.config.world.iron_count = int(self.iron_count_var.get())
        
        self.config.herbivores.count = int(self.herbivore_count_var.get())
        self.config.herbivores.max_energy = self.herbivore_max_energy_var.get()
        self.config.herbivores.initial_energy = self.herbivore_init_energy_var.get()
        self.config.herbivores.vision_range = self.herbivore_vision_var.get()
        
        self.config.predators.count = int(self.predator_count_var.get())
        self.config.predators.max_energy = self.predator_max_energy_var.get()
        self.config.predators.initial_energy = self.predator_init_energy_var.get()
        self.config.predators.vision_range = self.predator_vision_var.get()
        self.config.predators.attack_damage = self.predator_damage_var.get()
        self.config.predators.brain_type = self.predator_brain_var.get()
        
        self.config.herbivores.brain_type = self.herbivore_brain_var.get()

        self.config.smarts.count = int(self.smart_count_var.get())
        self.config.smarts.max_energy = self.smart_max_energy_var.get()
        self.config.smarts.initial_energy = self.smart_init_energy_var.get()
        self.config.smarts.vision_range = self.smart_vision_var.get()
        self.config.smarts.attack_damage = self.smart_damage_var.get()
        self.config.smarts.brain_type = self.smart_brain_var.get()
        
        self.result = self.config
        self.root.quit()
    
    def get_config(self):
        """Получить конфиг"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Warning: Error in Tkinter mainloop: {e}")
            return None
            
        # Убираем окно Tkinter из системы, чтобы оно не блокировало Pygame
        # (Проблема взаимодействия событийных циклов)
        try:
            self.root.destroy()
            while self.root.winfo_exists():
                self.root.update()
        except:
            pass
            
        return self.result
