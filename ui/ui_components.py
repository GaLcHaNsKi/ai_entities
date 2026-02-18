"""UI компоненты для интерфейса Pygame"""

import pygame


class Button:
    """Интерактивная кнопка"""
    
    def __init__(self, x: int, y: int, width: int, height: int, text: str, 
                 callback=None, font=None, color_bg=(100, 100, 100), 
                 color_hover=(120, 120, 120), color_text=(255, 255, 255)):
        """
        Создать кнопку
        
        Args:
            x, y: координаты верхнего левого угла
            width, height: ширина и высота
            text: текст на кнопке
            callback: функция, вызываемая при нажатии
            font: шрифт pygame
            color_bg: цвет фона
            color_hover: цвет при наведении
            color_text: цвет текста
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.font = font or pygame.font.Font(None, 24)
        self.color_bg = color_bg
        self.color_hover = color_hover
        self.color_text = color_text
        self.is_hovered = False
        self.is_pressed = False
    
    def draw(self, surface: pygame.Surface):
        """Отрисовать кнопку"""
        # Выбираем цвет в зависимости от состояния
        color = self.color_hover if self.is_hovered else self.color_bg
        
        # Рисуем фон
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)
        
        # Рисуем текст
        text_surface = self.font.render(self.text, True, self.color_text)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
    
    def update(self, mouse_pos: tuple, mouse_pressed: bool):
        """Обновить состояние кнопки
        
        Args:
            mouse_pos: позиция мыши (x, y)
            mouse_pressed: нажата ли левая кнопка мыши
        """
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Проверяем клик
        if self.is_hovered and mouse_pressed and not self.is_pressed:
            self.is_pressed = True
            if self.callback:
                self.callback()
        elif not mouse_pressed:
            self.is_pressed = False
    
    def handle_event(self, event: pygame.event.EventType) -> bool:
        """Обработать событие Pygame
        
        Returns:
            True если кнопка была нажата
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.rect.collidepoint(event.pos):
                    if self.callback:
                        self.callback()
                    return True
        return False


class ButtonGroup:
    """Группа кнопок"""
    
    def __init__(self):
        self.buttons = []
    
    def add_button(self, button: Button):
        """Добавить кнопку в группу"""
        self.buttons.append(button)
        return button
    
    def draw(self, surface: pygame.Surface):
        """Отрисовать все кнопки"""
        for button in self.buttons:
            button.draw(surface)
    
    def handle_events(self, mouse_pos: tuple, mouse_pressed: bool):
        """Обработать события для всех кнопок"""
        clicked_button = None
        for button in self.buttons:
            button.update(mouse_pos, mouse_pressed)
            if button.is_hovered and mouse_pressed and not button.is_pressed:
                clicked_button = button
        
        return clicked_button
    
    def clear(self):
        """Очистить группу"""
        self.buttons.clear()


class StatPanel:
    """Панель со статистикой"""
    
    def __init__(self, x: int, y: int, width: int, height: int, font=None, is_vertical=True):
        """Создать панель статистики
        
        Args:
            x, y, width, height: геометрия
            font: шрифт
            is_vertical: вертикальная (True) или горизонтальная (False) ориентация
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.font_title = font or pygame.font.Font(None, 28)
        self.font_text = pygame.font.Font(None, 24)
        self.is_vertical = is_vertical
        
        self.color_bg = (30, 30, 40)
        self.color_border = (60, 60, 70)
        self.color_text = (220, 220, 220)
        self.color_herbivore = (100, 200, 100)
        self.color_predator = (255, 100, 100)  # Ярче
        self.color_plant = (100, 200, 100)
        self.color_info = (100, 200, 255)
        
        self.stats = {}
        self.time = 0.0
        self.frame = 0
        self.paused = False
        self.speed = 1.0
    
    def update(self, stats: dict, time: float, frame: int, paused: bool, speed: float):
        """Обновить данные панели"""
        self.stats = stats
        self.time = time
        self.frame = frame
        self.paused = paused
        self.speed = speed
    
    def draw(self, surface: pygame.Surface):
        """Отрисовать панель"""
        # Рисуем фон
        pygame.draw.rect(surface, self.color_bg, self.rect)
        pygame.draw.rect(surface,(50, 50, 60), self.rect, 1) # Тонкая граница
        
        if self.is_vertical:
            self._draw_vertical(surface)
        else:
            self._draw_horizontal(surface)

    def _draw_vertical(self, surface):
        """Вертикальная отрисовка (старая)"""
        padding = 15
        x = self.rect.x + padding
        y = self.rect.y + padding
        line_height = 32
        
        # ... (код вертикальной отрисовки, можно оставить упрощенным если не нужен) ...
        # (Оставляю пустым так как мы переходим на горизонтальный, но структура поддерживает оба)
        
        # Заголовок
        title = self.font_title.render("STATISTICS", True, self.color_info)
        surface.blit(title, (x, y))
        y += line_height + 5
        
        # Статус
        status = "PAUSED" if self.paused else f"x{self.speed:.1f}"
        status_color = (255, 200, 0) if self.paused else (100, 255, 100)
        surface.blit(self.font_text.render(status, True, status_color), (x, y))
        y += line_height
        
        # Инфо
        surface.blit(self.font_text.render(f"H: {self.stats.get('herbivores_count', 0)}", True, self.color_herbivore), (x, y))
        y += line_height
        surface.blit(self.font_text.render(f"P: {self.stats.get('predators_count', 0)}", True, self.color_predator), (x, y))

    def _draw_horizontal(self, surface):
        """Горизонтальная отрисовка одной строкой"""
        y = self.rect.centery - 8  # Центрирование текста по вертикали (примерно)
        x = self.rect.x + 20
        spacing = 30
        
        # 1. Время и скорость
        time_str = f"{self.time:.1f}s"
        speed_str = "PAUSED" if self.paused else f"{self.speed:.1f}x"
        speed_color = (255, 200, 50) if self.paused else (100, 255, 100)
        
        surface.blit(self.font_text.render(f"T: {time_str}", True, self.color_text), (x, y))
        x += 100
        
        surface.blit(self.font_text.render(speed_str, True, speed_color), (x, y))
        x += 80 + spacing
        
        # Разделитель
        pygame.draw.line(surface, self.color_border, (x, self.rect.y + 10), (x, self.rect.y + self.rect.height - 10), 1)
        x += spacing
        
        # 2. Существа
        # Herbivores
        h_count = self.stats.get('herbivores_count', 0)
        surface.blit(self.font_text.render(f"Herbivores: {h_count}", True, self.color_herbivore), (x, y))
        x += 140
        
        # Predators
        p_count = self.stats.get('predators_count', 0)
        surface.blit(self.font_text.render(f"Predators: {p_count}", True, self.color_predator), (x, y))
        x += 130

        # Smart creatures
        s_count = self.stats.get('smarts_count', 0)
        surface.blit(self.font_text.render(f"Smarts: {s_count}", True, (120, 170, 255)), (x, y))
        x += 115
        
        # Plants
        plant_count = self.stats.get('plants_count', 0)
        surface.blit(self.font_text.render(f"Plants: {plant_count}", True, self.color_plant), (x, y))
        x += 120

        # Resources
        trees = self.stats.get('trees_count', 0)
        stones = self.stats.get('stones_count', 0)
        copper = self.stats.get('copper_count', 0)
        iron = self.stats.get('iron_count', 0)
        surface.blit(self.font_text.render(f"R(T/S/Cu/Fe): {trees}/{stones}/{copper}/{iron}", True, (170, 170, 185)), (x, y))
        x += 260 + spacing

        # Разделитель
        pygame.draw.line(surface, self.color_border, (x, self.rect.y + 10), (x, self.rect.y + self.rect.height - 10), 1)
        x += spacing
        
        # 3. Энергия (средняя)
        h_en = self.stats.get('herbivore_avg_energy', 0)
        p_en = self.stats.get('predator_avg_energy', 0)
        s_meat = self.stats.get('smart_avg_meat', 0)
        
        surface.blit(self.font_text.render(f"Avg Energy (H/P): {h_en:.0f} / {p_en:.0f}  |  Smart Meat: {s_meat:.0f}", True, (180, 180, 180)), (x, y))
