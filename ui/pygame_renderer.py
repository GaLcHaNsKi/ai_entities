"""Pygame визуализация симуляции с поддержкой камеры и зума"""

import pygame
import os
from core.physics import Vector2
from ui.ui_components import Button, ButtonGroup, StatPanel


class PygameRenderer:
    """Рендер симуляции на Pygame с полноэкранным режимом и камерой"""
    
    def __init__(self, fullscreen: bool = True):
        """Инициализация Pygame"""
        # Попытка центрировать окно
        try:
            os.environ['SDL_VIDEO_CENTERED'] = '1'
        except:
            pass
            
        pygame.init()
        
        # Получаем размер экрана
        if fullscreen:
            try:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except Exception as e:
                print(f"Fullscreen failed: {e}. Fallback to windowed mode.")
                self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        
        self.window_width, self.window_height = pygame.display.get_surface().get_size()
        pygame.display.set_caption("AI Entities - Ecosystem Simulation")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 32)
        
        # Цвета
        self.COLOR_BG = (25, 25, 35)
        self.COLOR_HERBIVORE = (100, 200, 100)
        self.COLOR_PREDATOR = (200, 100, 100)
        self.COLOR_SMART = (120, 170, 255)
        self.COLOR_PLANT = (80, 150, 80)
        self.COLOR_TREE = (70, 120, 70)
        self.COLOR_STONE = (130, 130, 140)
        self.COLOR_COPPER = (184, 115, 51)
        self.COLOR_IRON = (120, 140, 160)
        self.COLOR_TEXT = (200, 200, 200)
        self.COLOR_INFO = (150, 180, 200)
        
        # Масштабирование (1:1 по умолчанию)
        self.scale_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        
        # Камера (viewport) - смещение мира на экране
        self.camera_x = 0.0
        self.camera_y = 0.0
        
        # UI Layout
        self.TOP_BAR_HEIGHT = 50
        self.BOTTOM_BAR_HEIGHT = 60
        
        # UI компоненты - панель сверху горизонтально
        self.stat_panel = StatPanel(
            x=0,
            y=0,
            width=self.window_width,
            height=self.TOP_BAR_HEIGHT,
            font=self.font_large,
            is_vertical=False
        )
        
        # Кнопки управления - снизу
        self.buttons = ButtonGroup()
        self.button_play_pause = None
        self.button_speed_up = None
        self.button_speed_down = None
        self.button_reset = None
        self.button_quit = None
        self.button_stats = None
        
        self.show_stats_overlay = False
        
        self.setup_buttons()
        
        # Размер мира
        self.world_width = 500.0
        self.world_height = 500.0
        
        # Режим следования за мышью
        self.follow_mouse = False
        
        # Режим следования за скоплением существ
        self.auto_center_on_cluster = True  # Включен по умолчанию
        self.cluster_update_timer = 0  # Обновляем кластер каждые N кадров
        
        # Выбранное существо
        self.selected_entity = None
        self.info_panel_width = 250
        self.info_panel_height = 200
    
    def setup_buttons(self):
        """Установить кнопки горизонтально внизу"""
        self.buttons.clear()
        
        # Размеры кнопок
        btn_width = 140
        btn_height = 40
        spacing = 10
        
        # Центрируем кнопки
        total_width = (btn_width * 5) + (spacing * 4)
        start_x = (self.window_width - total_width) // 2
        y = self.window_height - 50  # Отступ снизу
        
        x = start_x
        
        # Play/Pause
        self.button_play_pause = self.buttons.add_button(Button(
            x, y, btn_width, btn_height, "PAUSE",
            font=self.font_small,
            color_bg=(80, 120, 80),
            color_hover=(100, 140, 100)
        ))
        x += btn_width + spacing
        
        # Speed Up
        self.button_speed_up = self.buttons.add_button(Button(
            x, y, btn_width, btn_height, "SPEED UP",
            font=self.font_small,
            color_bg=(100, 100, 120),
            color_hover=(120, 120, 140)
        ))
        x += btn_width + spacing
        
        # Speed Down
        self.button_speed_down = self.buttons.add_button(Button(
            x, y, btn_width, btn_height, "SPEED DOWN",
            font=self.font_small,
            color_bg=(100, 100, 120),
            color_hover=(120, 120, 140)
        ))
        x += btn_width + spacing
        
        # Reset
        self.button_reset = self.buttons.add_button(Button(
            x, y, btn_width, btn_height, "RESET",
            font=self.font_small,
            color_bg=(150, 100, 100),
            color_hover=(170, 120, 120)
        ))
        x += btn_width + spacing
        
        # Stats Overlay Button
        self.button_stats = self.buttons.add_button(Button(
            x, y, btn_width, btn_height, "STATS",
            font=self.font_small,
            color_bg=(100, 100, 150),
            color_hover=(120, 120, 180)
        ))
        x += btn_width + spacing

        # Quit
        self.button_quit = self.buttons.add_button(Button(
            x, y, btn_width, btn_height, "QUIT",
            font=self.font_small,
            color_bg=(180, 80, 80),
            color_hover=(200, 100, 100)
        ))
    
    def set_world_size(self, world_width: float, world_height: float):
        """Установить размер мира"""
        self.world_width = world_width
        self.world_height = world_height
        # Центрируем камеру на мир
        self.center_camera()
    
    def center_camera(self):
        """Центрировать камеру на мир"""
        world_view_width = self.world_width * self.scale_factor
        world_view_height = self.world_height * self.scale_factor
        
        viewport_height = self.window_height - self.TOP_BAR_HEIGHT - self.BOTTOM_BAR_HEIGHT
        
        self.camera_x = (world_view_width - self.window_width) / 2.0
        self.camera_y = (world_view_height - viewport_height) / 2.0
        
        # Ограничиваем камеру
        self.clamp_camera()
    
    def clamp_camera(self):
        """Ограничить камеру границами мира"""
        world_view_width = self.world_width * self.scale_factor
        world_view_height = self.world_height * self.scale_factor
        
        viewport_height = self.window_height - self.TOP_BAR_HEIGHT - self.BOTTOM_BAR_HEIGHT
        
        if world_view_width > self.window_width:
            self.camera_x = max(0, min(self.camera_x, world_view_width - self.window_width))
        else:
            self.camera_x = (world_view_width - self.window_width) / 2.0
            
        if world_view_height > viewport_height:
            self.camera_y = max(0, min(self.camera_y, world_view_height - viewport_height))
        else:
            self.camera_y = (world_view_height - viewport_height) / 2.0
    
    def find_largest_cluster(self, entities: list) -> tuple:
        """
        Найти центр самого большого скопления существ.
        Использует grid-based clustering для производительности.
        Возвращает (center_x, center_y) или (мир_x/2, мир_y/2) если нет существ
        """
        if not entities or len(entities) == 0:
            return (self.world_width / 2.0, self.world_height / 2.0)
        
        # Размер сетки для кластеризации (меньше = точнее, но медленнее)
        grid_size_x = max(10, int(self.world_width / 50))
        grid_size_y = max(10, int(self.world_height / 50))
        
        # Шаг ячейки
        cell_width = self.world_width / grid_size_x
        cell_height = self.world_height / grid_size_y
        
        # Счётчик существ в каждой ячейке
        grid = {}
        for entity in entities:
            if entity.is_alive:
                cell_x = int(entity.pos.x / cell_width)
                cell_y = int(entity.pos.y / cell_height)
                
                # Ограничиваем границами
                cell_x = max(0, min(cell_x, grid_size_x - 1))
                cell_y = max(0, min(cell_y, grid_size_y - 1))
                
                key = (cell_x, cell_y)
                grid[key] = grid.get(key, 0) + 1
        
        if not grid:
            return (self.world_width / 2.0, self.world_height / 2.0)
        
        # Находим ячейку с максимальным количеством существ
        max_cell = max(grid.keys(), key=lambda k: grid[k])
        
        # Центр этой ячейки в мировых координатах
        center_x = (max_cell[0] + 0.5) * cell_width
        center_y = (max_cell[1] + 0.5) * cell_height
        
        return (center_x, center_y)
    
    def center_on_cluster(self, cluster_center: tuple):
        """Центрировать камеру на заданной точке (центр скопления)"""
        center_x, center_y = cluster_center
        
        viewport_height = self.window_height - self.TOP_BAR_HEIGHT - self.BOTTOM_BAR_HEIGHT
        
        # Центр скопления должен быть в центре экрана (области просмотра)
        self.camera_x = center_x * self.scale_factor - self.window_width / 2.0
        self.camera_y = center_y * self.scale_factor - viewport_height / 2.0
        
        self.clamp_camera()

    def _smart_color_by_tribe(self, tribe_id: int) -> tuple:
        """Дать племени стабильный оттенок синего по его id."""
        base = self.COLOR_SMART
        # Детерминированный сдвиг без random
        shift = ((tribe_id * 37) % 60) - 30
        r = max(70, min(210, base[0] + shift // 2))
        g = max(110, min(230, base[1] + shift // 3))
        b = max(170, min(255, base[2] - shift // 4))
        return (r, g, b)

    def world_to_screen(self, pos: Vector2) -> tuple:
        """Преобразовать координаты мира в экранные с учётом камеры"""
        screen_x = int(pos.x * self.scale_factor - self.camera_x)
        screen_y = int(pos.y * self.scale_factor - self.camera_y) + self.TOP_BAR_HEIGHT
        return (screen_x, screen_y)
    
    def screen_to_world(self, screen_x: int, screen_y: int) -> Vector2:
        """Преобразовать экранные координаты в мировые"""
        world_x = (screen_x + self.camera_x) / self.scale_factor
        world_y = (screen_y - self.TOP_BAR_HEIGHT + self.camera_y) / self.scale_factor
        return Vector2(world_x, world_y)

    def update_cluster_position(self, world):
        """Обновить позицию камеры на кластере (вызывается из handle_events)"""
        try:
            if self.auto_center_on_cluster:
                self.cluster_update_timer += 1
                # Обновляем кластер каждые 10 кадров
                if self.cluster_update_timer >= 10:
                    self.cluster_update_timer = 0
                    all_creatures = [e for e in world.entities if e.is_alive]
                    if all_creatures:
                        cluster_center = self.find_largest_cluster(all_creatures)
                        self.center_on_cluster(cluster_center)
        except Exception as e:
            # Игнорируем ошибки в кластеризации, они не критичны
            pass

    def render(self, world, simulation_time: float = 0, paused: bool = False, speed: float = 1.0):
        """Отрисовать весь мир"""
        # Очищаем экран
        self.screen.fill((20, 20, 30))  # Темный фон
        
        # Область просмотра мира
        viewport_rect = pygame.Rect(0, self.TOP_BAR_HEIGHT, 
                                    self.window_width, 
                                    self.window_height - self.TOP_BAR_HEIGHT - self.BOTTOM_BAR_HEIGHT)
        
        # Ограничиваем рисование мира областью viewport
        self.screen.set_clip(viewport_rect)
        
        # Рисуем фон мира
        pygame.draw.rect(self.screen, self.COLOR_BG, viewport_rect)
        
        # Рисуем границы мира
        world_rect_screen = pygame.Rect(
            int(-self.camera_x),
            int(-self.camera_y) + self.TOP_BAR_HEIGHT,
            int(self.world_width * self.scale_factor),
            int(self.world_height * self.scale_factor)
        )
        pygame.draw.rect(self.screen, (50, 50, 60), world_rect_screen, 2)

        # Рисуем статические ресурсы
        for node in getattr(world, 'resources', []):
            if not node.is_alive:
                continue

            pos = self.world_to_screen(node.pos)
            if not viewport_rect.collidepoint(pos):
                continue

            if node.resource_type == "tree":
                radius = max(3, int(5 * self.scale_factor))
                pygame.draw.circle(self.screen, self.COLOR_TREE, pos, radius)
            elif node.resource_type == "stone":
                radius = max(3, int(4 * self.scale_factor))
                pygame.draw.circle(self.screen, self.COLOR_STONE, pos, radius)
            elif node.resource_type == "copper":
                radius = max(2, int(4 * self.scale_factor))
                pygame.draw.circle(self.screen, self.COLOR_COPPER, pos, radius)
            elif node.resource_type == "iron":
                radius = max(2, int(4 * self.scale_factor))
                pygame.draw.circle(self.screen, self.COLOR_IRON, pos, radius)
        
        # Рисуем растения
        for plant in world.plants:
            if plant.is_alive:
                pos = self.world_to_screen(plant.pos)
                if viewport_rect.collidepoint(pos):
                    size = max(2, int(3 * (plant.energy / plant.max_energy) * self.scale_factor))
                    pygame.draw.circle(self.screen, self.COLOR_PLANT, pos, size)
        
        # Рисуем травоядных
        herbivores = [e for e in world.entities if e.entity_type == "herbivore" and e.is_alive]
        for herbivore in herbivores:
            pos = self.world_to_screen(herbivore.pos)
            if viewport_rect.collidepoint(pos):
                size = max(3, int((4 + (herbivore.energy / herbivore.max_energy) * 3) * self.scale_factor))
                pygame.draw.circle(self.screen, self.COLOR_HERBIVORE, pos, size)
                
                # Рисуем направление
                if herbivore.velocity.magnitude() > 0:
                    rotation = herbivore.velocity.normalize()
                    end_pos = (
                        pos[0] + int(rotation.x * 15 * self.scale_factor),
                        pos[1] + int(rotation.y * 15 * self.scale_factor)
                    )
                    pygame.draw.line(self.screen, self.COLOR_HERBIVORE, pos, end_pos, 1)
        
        # Рисуем хищников
        predators = [e for e in world.entities if e.entity_type == "predator" and e.is_alive]
        for predator in predators:
            pos = self.world_to_screen(predator.pos)
            if viewport_rect.collidepoint(pos):
                size = max(4, int((5 + (predator.energy / predator.max_energy) * 4) * self.scale_factor))
                pygame.draw.circle(self.screen, self.COLOR_PREDATOR, pos, size)
                
                # Рисуем направление
                if predator.velocity.magnitude() > 0:
                    rotation = predator.velocity.normalize()
                    end_pos = (
                        pos[0] + int(rotation.x * 20 * self.scale_factor),
                        pos[1] + int(rotation.y * 20 * self.scale_factor)
                    )
                    pygame.draw.line(self.screen, self.COLOR_PREDATOR, pos, end_pos, 1)

        # Рисуем разумных существ
        smarts = [e for e in world.entities if e.entity_type == "smart" and e.is_alive]
        for smart in smarts:
            pos = self.world_to_screen(smart.pos)
            if viewport_rect.collidepoint(pos):
                size = max(3, int((4 + (smart.energy / smart.max_energy) * 3) * self.scale_factor))
                tribe_color = self._smart_color_by_tribe(getattr(smart, 'tribe_id', 0))
                pygame.draw.circle(self.screen, tribe_color, pos, size)

                # Индикатор запаса мяса над существом
                meat_cap = max(1.0, getattr(smart, 'meat_capacity', 1.0))
                meat_ratio = min(1.0, max(0.0, getattr(smart, 'meat_inventory', 0.0) / meat_cap))
                bar_w = max(10, int(14 * self.scale_factor))
                bar_h = max(2, int(3 * self.scale_factor))
                bar_x = pos[0] - bar_w // 2
                bar_y = pos[1] - size - 7
                pygame.draw.rect(self.screen, (60, 60, 70), (bar_x, bar_y, bar_w, bar_h))
                fill_w = int(bar_w * meat_ratio)
                if fill_w > 0:
                    pygame.draw.rect(self.screen, (210, 90, 90), (bar_x, bar_y, fill_w, bar_h))

                if smart.velocity.magnitude() > 0:
                    rotation = smart.velocity.normalize()
                    end_pos = (
                        pos[0] + int(rotation.x * 16 * self.scale_factor),
                        pos[1] + int(rotation.y * 16 * self.scale_factor)
                    )
                    pygame.draw.line(self.screen, tribe_color, pos, end_pos, 1)
        
        # Рисуем выделение вокруг выбранного существа
        if self.selected_entity and self.selected_entity.is_alive:
            sel_pos = self.world_to_screen(self.selected_entity.pos)
            if viewport_rect.collidepoint(sel_pos):
                # Яркий желтый круг с пульсацией
                import time
                pulse = 2 + abs(3 * pygame.math.Vector2(1, 0).rotate(time.time() * 100).x)
                sel_size = max(8, int((10 + pulse) * self.scale_factor))
                pygame.draw.circle(self.screen, (255, 255, 100), sel_pos, sel_size, 2)
        
        # Снимаем ограничение рисования
        self.screen.set_clip(None)
        
        # === UI INTERFACE ===
        
        # Нижняя панель
        bottom_rect = pygame.Rect(0, self.window_height - self.BOTTOM_BAR_HEIGHT, self.window_width, self.BOTTOM_BAR_HEIGHT)
        pygame.draw.rect(self.screen, (35, 35, 45), bottom_rect)
        pygame.draw.line(self.screen, (60, 60, 70), (0, bottom_rect.y), (self.window_width, bottom_rect.y), 1)

        # Обновляем статистику (Верхняя панель)
        stats = world.get_stats()
        
        if stats['herbivores_count'] > 0:
            h_energy = sum(e.energy for e in world.entities if e.entity_type == "herbivore") / stats['herbivores_count']
            stats['herbivore_avg_energy'] = h_energy
        
        if stats['predators_count'] > 0:
            p_energy = sum(e.energy for e in world.entities if e.entity_type == "predator") / stats['predators_count']
            stats['predator_avg_energy'] = p_energy

        if stats.get('smarts_count', 0) > 0:
            s_meat = sum(getattr(e, 'meat_inventory', 0.0) for e in world.entities if e.entity_type == "smart") / stats['smarts_count']
            stats['smart_avg_meat'] = s_meat
        
        self.stat_panel.update(stats, simulation_time, world.frame, paused, speed)
        self.stat_panel.draw(self.screen)
        
        # Кнопки (в центре снизу)
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        self.buttons.handle_events(mouse_pos, mouse_pressed)
        self.buttons.draw(self.screen)
        
        # Текст на кнопке Play/Pause
        if self.button_play_pause:
            self.button_play_pause.text = "▶ PLAY" if paused else "⏸ PAUSE"
        
        # Инфо слева внизу
        zoom_text = self.font_small.render(f"Zoom: {self.scale_factor:.1f}x", True, (150, 150, 150))
        self.screen.blit(zoom_text, (20, self.window_height - 32))
        
        # Инфо справа внизу (режимы)
        modes_x = self.window_width - 120
        y_text = self.window_height - 40
        
        follow_text = "Edge Panning" if self.follow_mouse else ""
        if follow_text:
            follow_surf = self.font_small.render(follow_text, True, (100, 255, 100))
            self.screen.blit(follow_surf, (modes_x, y_text))
            y_text += 15
        
        cluster_text = "Cluster View" if self.auto_center_on_cluster else ""
        if cluster_text:
            cluster_surf = self.font_small.render(cluster_text, True, (100, 200, 255))
            self.screen.blit(cluster_surf, (modes_x, y_text))

        if self.show_stats_overlay:
            self.draw_stats_overlay(world)
        
        # Отображаем информацию о выбранном существе
        if self.selected_entity and self.selected_entity.is_alive:
            self.draw_entity_info_panel(self.selected_entity)
        
        pygame.display.flip()

    def draw_stats_overlay(self, world):
        """Отрисовать модальное окно статистики по ресурсам и строениям"""
        # Сбор данных
        resource_totals = {}
        building_totals = {}
        tool_totals = {}
        
        smarts = [e for e in world.entities if e.entity_type == "smart" and e.is_alive]
        
        # Подсчет строений
        if hasattr(world, 'buildings'):
            for b in world.buildings:
                if not b.is_destroyed():
                    b_name = b.type.value if hasattr(b.type, 'value') else str(b.type)
                    building_totals[b_name] = building_totals.get(b_name, 0) + 1

        # Подсчет инвентаря и экипировки
        for s in smarts:
            if hasattr(s, 'inventory'):
                for item, count in s.inventory.get_contents().items():
                    i_name = item.value if hasattr(item, 'value') else str(item)
                    # Простая эвристика классификации
                    if "pickaxe" in i_name or "axe" in i_name or "spear" in i_name:
                        tool_totals[i_name] = tool_totals.get(i_name, 0) + count
                    else:
                        resource_totals[i_name] = resource_totals.get(i_name, 0) + count
            
            if hasattr(s, 'equipped'):
                if hasattr(s.equipped, 'values'): # Dict check
                    for item in s.equipped.values():
                        if item:
                            i_name = item.value if hasattr(item, 'value') else str(item)
                            tool_totals[i_name] = tool_totals.get(i_name, 0) + 1

        # === Отрисовка Модального Окна ===
        
        # Затемнение фона
        overlay = pygame.Surface((self.window_width, self.window_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Размеры окна
        modal_w = 800
        modal_h = 500
        modal_x = (self.window_width - modal_w) // 2
        modal_y = (self.window_height - modal_h) // 2
        
        # Фон окна
        pygame.draw.rect(self.screen, (40, 40, 50), (modal_x, modal_y, modal_w, modal_h))
        pygame.draw.rect(self.screen, (100, 100, 120), (modal_x, modal_y, modal_w, modal_h), 2)
        
        # Заголовок
        title_font = self.font_large
        title = title_font.render(f"Simulation Statistics (Agents: {len(smarts)})", True, (255, 255, 255))
        self.screen.blit(title, (modal_x + 20, modal_y + 20))
        
        # Колонки
        col_width = (modal_w - 40) // 3
        start_y = modal_y + 70
        
        # Функция отрисовки колонки
        def draw_column(title, data, col_idx, color_title=(200, 200, 255)):
            x = modal_x + 20 + col_idx * col_width
            y = start_y
            
            # Заголовок колонки
            head = self.font_small.render(title, True, color_title)
            self.screen.blit(head, (x, y))
            y += 25
            
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
            for name, count in sorted_items:
                display_name = name.replace('_', ' ').title()
                txt = self.font_small.render(f"{display_name}: {count}", True, (220, 220, 220))
                self.screen.blit(txt, (x, y))
                y += 20
        
        draw_column("Resources", resource_totals, 0, (100, 255, 100))
        draw_column("Buildings", building_totals, 1, (255, 200, 100))
        draw_column("Tools & Gear", tool_totals, 2, (100, 200, 255))
        
        # Подсказка закрытия
        hint = self.font_small.render("Press 'STATS' button or click outside to close", True, (150, 150, 150))
        self.screen.blit(hint, (modal_x + 20, modal_y + modal_h - 30))

    
    def get_entity_at_position(self, world, screen_x: int, screen_y: int):
        """Найти существо под позицией мыши (в координатах снимать → мир)"""
        if world is None:
            return None
        
        # Преобразуем экранные координаты в мировые
        world_x = screen_x / self.scale_factor + self.camera_x
        world_y = screen_y / self.scale_factor + self.camera_y
        
        # Ищем ближайшее существо к клику (в радиусе 15 пикселей)
        click_radius = 15.0 / self.scale_factor
        closest_entity = None
        closest_dist = click_radius
        
        for entity in world.entities:
            if not entity.is_alive:
                continue
            dx = entity.pos.x - world_x
            dy = entity.pos.y - world_y
            dist = (dx*dx + dy*dy)**0.5
            
            if dist < closest_dist:
                closest_entity = entity
                closest_dist = dist
        
        return closest_entity
    
    def draw_entity_info_panel(self, entity):
        """Нарисовать панель с информацией о выбранном существе"""
        if entity is None or not entity.is_alive:
            return
        
        # Позиция панели - верхний правый угол
        panel_x = self.window_width - self.info_panel_width - 10
        panel_y = self.TOP_BAR_HEIGHT + 10
        
        # Фон панели
        panel_rect = pygame.Rect(panel_x, panel_y, self.info_panel_width, self.info_panel_height)
        pygame.draw.rect(self.screen, (50, 50, 60), panel_rect)
        pygame.draw.rect(self.screen, (150, 150, 150), panel_rect, 2)  # Border
        
        # Текст информации
        entity_type = entity.entity_type.upper()
        color_type = {
            "herbivore": (100, 200, 100),
            "predator": (200, 100, 100),
            "smart": (120, 170, 255),
        }.get(entity.entity_type, (180, 180, 180))
        
        lines = [
            (f"[{entity_type}]", color_type, 12),
            (f"ID: {entity.id[:8]}...", (200, 200, 200), 8),
            ("", (0, 0, 0), 8),  # Пустая строка
            (f"Pos: ({entity.pos.x:.1f}, {entity.pos.y:.1f})", (200, 200, 200), 8),
            (f"Speed: {entity.velocity.magnitude():.1f}", (200, 200, 200), 8),
            (f"Energy: {entity.energy:.1f}/{entity.max_energy:.1f}", (200, 200, 200), 8),
        ]
        
        # Здоровье (если существо его имеет)
        if hasattr(entity, 'health') and hasattr(entity, 'max_health'):
            lines.append((f"Health: {entity.health:.1f}/{entity.max_health:.1f}", (200, 200, 200), 8))
        
        lines.extend([
            (f"Age: {entity.age:.2f}s", (200, 200, 200), 8),
        ])
        
        # Добавляем состояние
        if hasattr(entity, 'state'):
            lines.append((f"State: {entity.state}", (200, 200, 150), 8))
        
        # Рисуем текст
        y_offset = panel_y + 8
        for text, color, size in lines:
            if text == "":
                y_offset += 8
                continue
            font = pygame.font.Font(None, 18 + (size - 8))
            text_surf = font.render(text, True, color)
            self.screen.blit(text_surf, (panel_x + 8, y_offset))
            y_offset += 20
    
    def handle_events(self, world=None) -> dict:
        """Обработать события Pygame"""
        events = {
            'quit': False,
            'pause': False,
            'speed_up': False,
            'speed_down': False,
            'reset': False
        }
        
        # Обновляем позицию кластера перед обработкой событий
        if world is not None:
            self.update_cluster_position(world)
        
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        # Обработка кнопок мышью
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                events['quit'] = True
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    if self.button_play_pause and self.button_play_pause.rect.collidepoint(event.pos):
                        events['pause'] = True
                    elif self.button_speed_up and self.button_speed_up.rect.collidepoint(event.pos):
                        events['speed_up'] = True
                    elif self.button_speed_down and self.button_speed_down.rect.collidepoint(event.pos):
                        events['speed_down'] = True
                    elif self.button_reset and self.button_reset.rect.collidepoint(event.pos):
                        events['reset'] = True
                    elif self.button_stats and self.button_stats.rect.collidepoint(event.pos):
                        self.show_stats_overlay = not self.show_stats_overlay
                    elif self.button_quit and self.button_quit.rect.collidepoint(event.pos):
                        events['quit'] = True
                    else:
                        # Кличем по миру - пытаемся выбрать существо
                        # Но пропускаем верхнюю панель кнопок
                        if event.pos[1] > self.BOTTOM_BAR_HEIGHT:
                            entity = self.get_entity_at_position(world, event.pos[0], event.pos[1] - self.TOP_BAR_HEIGHT)
                            self.selected_entity = entity
                            if entity and entity.is_alive:
                                self.auto_center_on_cluster = False  # Отключаем автоцентр при выборе существа

                
                # Колесо вверх - зум вперед
                elif event.button == 4:
                    old_scale = self.scale_factor
                    self.scale_factor = min(self.max_zoom, self.scale_factor * 1.2)
                    # Зум в сторону мыши
                    self.zoom_at_mouse(mouse_x, mouse_y, old_scale)
                
                # Колесо вниз - зум назад
                elif event.button == 5:
                    old_scale = self.scale_factor
                    self.scale_factor = max(self.min_zoom, self.scale_factor / 1.2)
                    self.zoom_at_mouse(mouse_x, mouse_y, old_scale)
                
                # Right click - отменить выделение
                elif event.button == 3:
                    self.selected_entity = None
                    self.auto_center_on_cluster = True  # Вернуть автоцентр
            
            elif event.type == pygame.VIDEORESIZE:
                # Обновляем поверхность при изменении размера
                self.window_width, self.window_height = event.w, event.h
                self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
                
                # Обновляем UI
                self.stat_panel.rect.width = self.window_width
                self.setup_buttons()
                
                # Пересчитываем границы камеры
                self.clamp_camera()
                
            # Горячие клавиши
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    events['pause'] = True
                elif event.key == pygame.K_q:
                    events['quit'] = True
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    events['speed_up'] = True
                elif event.key == pygame.K_MINUS:
                    events['speed_down'] = True
                elif event.key == pygame.K_r:
                    events['reset'] = True
                elif event.key == pygame.K_m:  # M - toggle mouse follow
                    self.follow_mouse = not self.follow_mouse
                elif event.key == pygame.K_c:  # C - toggle cluster auto-center
                    self.auto_center_on_cluster = not self.auto_center_on_cluster
                elif event.key == pygame.K_HOME:  # Home - центрировать камеру
                    self.center_camera()
        
        # Следование за мышью (Edge Panning - сдвиг при приближении к краю)
        if self.follow_mouse:
            # Когда включено следование за мышью, отключаем автоцентрирование на кластер
            self.auto_center_on_cluster = False
            
            pan_margin = 50  # Граница в пикселях (активная зона)
            pan_speed = 15   # Скорость сдвига камеры
            
            # Сдвиг влево
            if mouse_x < pan_margin:
                self.camera_x -= pan_speed
            # Сдвиг вправо
            if mouse_x > self.window_width - pan_margin:
                self.camera_x += pan_speed
            # Сдвиг вверх
            if mouse_y < pan_margin + self.TOP_BAR_HEIGHT:
                self.camera_y -= pan_speed
            # Сдвиг вниз
            if mouse_y > self.window_height - pan_margin - self.BOTTOM_BAR_HEIGHT:
                self.camera_y += pan_speed
        
        self.clamp_camera()
        return events
    
    def zoom_at_mouse(self, mouse_x: int, mouse_y: int, old_scale: float):
        """Зум в сторону мыши"""
        # Мировые координаты мыши ДО зума
        world_before = self.screen_to_world(mouse_x, mouse_y)
        
        # После изменения scale_factor, пересчитываем камеру
        # чтобы мышь оставалась на том же месте мира
        world_after_x = world_before.x
        world_after_y = world_before.y
        
        # Нужная позиция камеры
        self.camera_x = world_after_x * self.scale_factor - mouse_x
        self.camera_y = world_after_y * self.scale_factor - mouse_y + self.TOP_BAR_HEIGHT
        
        self.clamp_camera()
    
    def set_fps(self, fps: int):
        """Установить FPS"""
        self.clock.tick(fps)
    
    def quit(self):
        """Закрыть Pygame"""
        pygame.quit()
