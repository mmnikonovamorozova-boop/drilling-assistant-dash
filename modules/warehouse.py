"""
МОДУЛЬ "ЖИВОЙ СКЛАД"
Парсинг Excel-отчета инженеров и поиск альтернатив для КНБК
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WarehouseItem:
    """Элемент складского учета"""
    def __init__(self, row_dict: dict):
        self.name = row_dict.get('Наименование', '')
        self.status = row_dict.get('статус', '')  # Аренда/Собственное
        self.equipment_name = row_dict.get('Номер', '')  # Наименование, номер, длина по паспорту
        self.actual_length = self._parse_float(row_dict.get('Фактическая длина, м', 0))
        self.weight = self._parse_float(row_dict.get('Вес, кг', 0))
        self.delivery_date = row_dict.get('Дата завоза оборудования', '')
        self.last_defect_date = row_dict.get('Дата последней дефектоскопии', '')
        self.hours_after_defect = self._parse_float(row_dict.get('Наработка после последней дефектоскопии', 0))
        self.total_hours = self._parse_float(row_dict.get('Общая наработка', 0))
        self.remaining_hours = self._parse_float(row_dict.get('остаток, ч', 0))
        self.diameter_mm = self._parse_float(row_dict.get('Диаметр, мм', 0))
        self.max_hours = self._parse_float(row_dict.get('максимальное время, ч', 0))
        
        # Определяем тип элемента по названию
        self.element_type = self._detect_element_type()
        
        # Статус годности
        self.is_ready = self._check_readiness()
    
    def _parse_float(self, value) -> float:
        """Безопасный парсинг чисел"""
        try:
            if pd.isna(value):
                return 0.0
            return float(str(value).replace(',', '.'))
        except:
            return 0.0
    
    def _detect_element_type(self) -> str:
        """Определяет тип элемента по названию"""
        name_lower = self.name.lower() + ' ' + self.equipment_name.lower()
        
        if 'взд' in name_lower or 'забойный двигатель' in name_lower:
            return 'ВЗД'
        elif 'переводник' in name_lower or 'пп ' in name_lower or 'пм ' in name_lower:
            return 'Переводник'
        elif 'нубт' in name_lower or 'утяжеленная' in name_lower:
            return 'НУБТ'
        elif 'тбт' in name_lower or 'труба бурильная' in name_lower:
            return 'ТБТ'
        elif 'сбт' in name_lower:
            return 'СБТ'
        elif 'долото' in name_lower:
            return 'Долото'
        elif 'стабилизатор' in name_lower or 'калибратор' in name_lower:
            return 'Стабилизатор'
        elif 'муд' in name_lower or 'mwd' in name_lower:
            return 'MWD'
        else:
            return 'Прочее'
    
    def _check_readiness(self) -> bool:
        """Проверяет готовность к работе"""
        # Готов если: остаток часов > 0, есть дата дефектоскопии, статус не "Брак"
        if self.remaining_hours <= 0:
            return False
        if 'брак' in self.status.lower() or 'ремонт' in self.status.lower():
            return False
        if not self.last_defect_date or self.last_defect_date == 'nan':
            return False
        return True
    
    def to_dict(self) -> dict:
        """Сериализация для отображения"""
        return {
            'Наименование': self.name,
            'Тип': self.element_type,
            'Статус': self.status,
            'Номер/Описание': self.equipment_name,
            'Факт. длина, м': self.actual_length,
            'Вес, кг': self.weight,
            'Дата завоза': self.last_defect_date,
            'Наработка, ч': self.total_hours,
            'Остаток, ч': self.remaining_hours,
            'Диаметр, мм': self.diameter_mm,
            'Готов к работе': '✅ Да' if self.is_ready else '❌ Нет'
        }


class WarehouseManager:
    """Менеджер складского учета"""
    
    def __init__(self):
        self.items: List[WarehouseItem] = []
        self.db_path = Path("data/warehouse_inventory.db")
        self.last_update = None
    
    def load_from_excel(self, file_path: str) -> bool:
        """
        Загружает складской отчет из Excel
        Формат: таблица с колонками как в отчете инженеров
        """
        try:
            # Читаем Excel с учетом возможных объединенных ячеек
            df = pd.read_excel(file_path, header=None)
            
            # Находим строку с заголовками (обычно 2-я или 3-я строка)
            header_row_idx = None
            for idx, row in df.iterrows():
                row_str = ' '.join([str(cell) for cell in row.values])
                if 'Наименование' in row_str and 'статус' in row_str.lower():
                    header_row_idx = idx
                    break
            
            if header_row_idx is None:
                logger.error("Не найдена строка заголовков")
                return False
            
            # Извлекаем заголовки
            headers = []
            for cell in df.iloc[header_row_idx].values:
                headers.append(str(cell).strip() if pd.notna(cell) else '')
            
            # Читаем данные со следующей строки
            data_df = df.iloc[header_row_idx + 1:].copy()
            data_df.columns = headers[:len(data_df.columns)]
            
            # Удаляем пустые строки
            data_df = data_df[data_df['Наименование'].notna()]
            data_df = data_df[data_df['Наименование'].str.strip() != '']
            
            # Создаем объекты WarehouseItem
            self.items = []
            for _, row in data_df.iterrows():
                try:
                    item = WarehouseItem(row.to_dict())
                    if item.name:  # Пропускаем полностью пустые
                        self.items.append(item)
                except Exception as e:
                    logger.warning(f"Ошибка парсинга строки: {e}")
                    continue
            
            self.last_update = datetime.now()
            logger.info(f"Загружено {len(self.items)} элементов со склада")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel: {e}")
            return False
    
    def search_by_type(self, element_type: str, ready_only: bool = True) -> List[WarehouseItem]:
        """Поиск элементов по типу"""
        filtered = [item for item in self.items if item.element_type == element_type]
        if ready_only:
            filtered = [item for item in filtered if item.is_ready]
        return filtered
    
    def search_crossover(self, od_top: float, od_bot: float, tolerance: float = 2.0) -> Optional[WarehouseItem]:
        """
        Поиск переводника (crossover) для соединения двух элементов с разными диаметрами
        od_top: диаметр верхнего элемента, мм
        od_bot: диаметр нижнего элемента, мм
        tolerance: допуск по диаметру, мм
        """
        # Ищем переводники
        crossovers = self.search_by_type('Переводник', ready_only=True)
        
        for item in crossovers:
            # Проверяем, подходит ли переводник по диаметрам
            # Обычно в названии переводника указаны диаметры: "ПП 172/165"
            name_lower = item.equipment_name.lower() + ' ' + item.name.lower()
            
            # Парсим диаметры из названия
            import re
            diameters = re.findall(r'(\d{2,3})[/.](\d{2,3})', name_lower)
            
            if diameters:
                for d1, d2 in diameters:
                    d1, d2 = float(d1), float(d2)
                    # Проверяем оба варианта (прямой и обратный)
                    if (abs(d1 - od_top) <= tolerance and abs(d2 - od_bot) <= tolerance) or \
                       (abs(d1 - od_bot) <= tolerance and abs(d2 - od_top) <= tolerance):
                        return item
        
        return None
    
    def get_statistics(self) -> dict:
        """Статистика по складу"""
        total = len(self.items)
        ready = len([i for i in self.items if i.is_ready])
        by_type = {}
        for item in self.items:
            by_type[item.element_type] = by_type.get(item.element_type, 0) + 1
        
        return {
            'total': total,
            'ready': ready,
            'not_ready': total - ready,
            'by_type': by_type,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def get_all_items_table(self) -> pd.DataFrame:
        """Возвращает все элементы в виде таблицы для отображения"""
        return pd.DataFrame([item.to_dict() for item in self.items])


# Глобальный экземпляр менеджера
warehouse_manager = WarehouseManager()


def create_warehouse_upload_section():
    """Создает компонент загрузки складского Excel"""
    from dash import html, dcc
    import dash_bootstrap_components as dbc
    
    return html.Div([
        html.H4("📦 Модуль 'Живой склад'", style={"color": "#0f172a", "marginBottom": "15px"}),
        
        dbc.Card([
            dbc.CardHeader(html.H5("Загрузка складского отчета", style={"margin": "0"})),
            dbc.CardBody([
                html.P("Загрузите актуальный Excel-файл учета оборудования с мостков:", 
                      style={"marginBottom": "15px"}),
                
                dcc.Upload(
                    id='warehouse-upload',
                    children=html.Div([
                        '📁 Перетащите Excel-файл сюда или ',
                        html.A('выберите файл', style={"color": "#2563eb", "textDecoration": "underline"})
                    ]),
                    style={
                        'width': '100%',
                        'height': '80px',
                        'lineHeight': '80px',
                        'borderWidth': '2px',
                        'borderStyle': 'dashed',
                        'borderRadius': '8px',
                        'textAlign': 'center',
                        'backgroundColor': '#f8fafc',
                        'cursor': 'pointer'
                    },
                    multiple=False
                ),
                
                html.Div(id='warehouse-upload-status', style={"marginTop": "15px"}),
                
                html.Div(id='warehouse-statistics', style={"marginTop": "20px"}),
            ])
        ]),
        
        html.Div(id='warehouse-items-table', style={"marginTop": "20px"}),
    ])


def create_alternative_suggestion(critical_joint: dict) -> html.Div:
    """
    Создает компонент с предложением альтернативы при критическом стыке
    critical_joint: {"idx": 1, "top": "ТБТ-172", "bot": "НУБТ-165", "delta": 7.0, "od_top": 172.0, "od_bot": 165.0}
    """
    from dash import html
    import dash_bootstrap_components as dbc
    
    # Ищем переводник
    crossover = warehouse_manager.search_crossover(
        od_top=critical_joint.get('od_top', 0),
        od_bot=critical_joint.get('od_bot', 0)
    )
    
    if crossover:
        # Найдена альтернатива
        return html.Div([
            html.H5("✅ Найдено решение на складе:", style={"color": "#16a34a", "marginBottom": "10px"}),
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Strong("Наименование: "),
                        html.Span(crossover.equipment_name),
                    ], style={"marginBottom": "8px"}),
                    
                    html.Div([
                        html.Strong("Тип: "),
                        html.Span(crossover.element_type),
                    ], style={"marginBottom": "8px"}),
                    
                    html.Div([
                        html.Strong("Остаток ресурса: "),
                        html.Span(f"{crossover.remaining_hours:.0f} ч", 
                                 style={"color": "#16a34a", "fontWeight": "bold"}),
                    ], style={"marginBottom": "8px"}),
                    
                    html.Div([
                        html.Strong("Дата последней дефектоскопии: "),
                        html.Span(crossover.last_defect_date),
                    ]),
                ])
            ]),
            
            html.Button("➕ Добавить в сборку КНБК", 
                       id='btn-add-crossover',
                       className="action-btn btn-primary",
                       style={"marginTop": "15px", "width": "100%"}),
        ], style={"padding": "15px", "backgroundColor": "#f0fdf4", "borderRadius": "8px", 
                 "border": "2px solid #16a34a"})
    
    else:
        # Альтернатива не найдена
        return html.Div([
            html.H5("❌ Альтернатива не найдена на складе", style={"color": "#dc2626", "marginBottom": "10px"}),
            html.P(f"Для устранения критического перепада {critical_joint.get('delta', 0):.1f} мм "
                  f"требуется переводник с диаметрами {critical_joint.get('od_top', 0):.0f}/{critical_joint.get('od_bot', 0):.0f} мм.",
                  style={"marginBottom": "15px"}),
            html.Div([
                html.Strong("Рекомендация: "),
                html.Span("Заказать переводник с центральной базы или использовать ручную подгонку стыка."),
            ], style={"backgroundColor": "#fef2f2", "padding": "10px", "borderRadius": "6px"}),
        ], style={"padding": "15px", "backgroundColor": "#fef2f2", "borderRadius": "8px", 
                 "border": "2px solid #dc2626"})


def warehouse_callbacks(app, data_bridge):
    """Регистрирует callback'и для модуля склада"""
    from dash import Input, Output, State
    import base64
    import io
    
    @app.callback(
        [Output('warehouse-upload-status', 'children'),
         Output('warehouse-statistics', 'children'),
         Output('warehouse-items-table', 'children')],
        Input('warehouse-upload', 'contents'),
        State('warehouse-upload', 'filename'),
        prevent_initial_call=True
    )
    def handle_warehouse_upload(contents, filename):
        if contents is None:
            return None, None, None
        
        try:
            # Декодируем содержимое файла
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            # Сохраняем во временный файл
            temp_path = Path(f"data/temp_{filename}")
            temp_path.parent.mkdir(exist_ok=True)
            temp_path.write_bytes(decoded)
            
            # Загружаем в менеджер
            success = warehouse_manager.load_from_excel(str(temp_path))
            
            if success:
                stats = warehouse_manager.get_statistics()
                df_items = warehouse_manager.get_all_items_table()
                
                status_msg = html.Div(
                    f"✅ Файл '{filename}' успешно загружен! Обработано элементов: {stats['total']}",
                    style={"color": "#16a34a", "fontWeight": "bold"}
                )
                
                stats_display = html.Div([
                    html.H6("Статистика склада:", style={"marginBottom": "10px"}),
                    html.P(f"Всего позиций: {stats['total']}"),
                    html.P(f"Готовы к работе: {stats['ready']}"),
                    html.P(f"Требуют внимания: {stats['not_ready']}"),
                    html.P(f"Последнее обновление: {stats['last_update'][:19] if stats['last_update'] else 'Н/Д'}"),
                ])
                
                # Таблица элементов
                items_table = html.Div([
                    html.H6("Элементы на складе:", style={"marginBottom": "10px"}),
                    html.Pre(df_items.head(20).to_string(index=False),
                            style={"backgroundColor": "#f8fafc", "padding": "10px", "borderRadius": "6px",
                                  "fontSize": "12px", "overflow": "auto"})
                ])
                
                # Удаляем временный файл
                temp_path.unlink()
                
                return status_msg, stats_display, items_table
            else:
                return html.Div("❌ Ошибка парсинга файла. Проверьте формат.", 
                               style={"color": "#dc2626"}), None, None
        
        except Exception as e:
            logger.error(f"Ошибка загрузки склада: {e}")
            return html.Div(f"❌ Ошибка: {str(e)}", style={"color": "#dc2626"}), None, None
