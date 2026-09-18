"""
МОДУЛЬ ТЕЛЕМЕТРИЧЕСКИХ СИСТЕМ В КНБК
Расчет магнитных помех, позиционирование датчиков в резистивиметре,
влияние ферромагнитных элементов на инклинометр.

Основан на:
- API RP 7G (Рекомендуемая практика для буровых труб)
- IADC (Международная ассоциация буровых подрядчиков)
- Практика NOV, Smith Services, Baker Hughes
"""
import math
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np

# ============================================================================
# БАЗА ДАННЫХ ТИПОВЫХ КОНФИГУРАЦИЙ КНБК С ТС
# ============================================================================

TYPICAL_BHA_CONFIGS = {
    "Вертикальное бурение с MWD": {
        "description": "Стандартная КНБК для вертикального бурения с телеметрией",
        "elements": [
            {"name": "Долото PDC", "length": 0.3, "magnetic": False},
            {"name": "ВЗД", "length": 8.5, "magnetic": True, "magnetic_moment": 15.0},
            {"name": "Non-Mag Sub (NMDC)", "length": 9.1, "magnetic": False},
            {"name": "MWD (Gamma + Inclination)", "length": 6.0, "magnetic": False},
            {"name": "Non-Mag Sub (NMDC)", "length": 9.1, "magnetic": False},
            {"name": "УЗС", "length": 8.9, "magnetic": True, "magnetic_moment": 8.0},
            {"name": "НУБТ", "length": 9.1, "magnetic": True, "magnetic_moment": 5.0},
        ],
        "total_length": 51.0,
        "sensor_positions": [
            {"name": "Инклинометр MWD", "offset_from_bit": 23.9, "in_nm_sub": True}
        ]
    },
    
    "Горизонтальное бурение с RSS": {
        "description": "КНБК для горизонтального бурения с роторной управляемой системой",
        "elements": [
            {"name": "Долото PDC", "length": 0.3, "magnetic": False},
            {"name": "RSS (Near-Bit)", "length": 3.5, "magnetic": False},
            {"name": "Non-Mag Sub (NMDC)", "length": 9.1, "magnetic": False},
            {"name": "MWD (Gamma + Inclination + Azimuth)", "length": 6.0, "magnetic": False},
            {"name": "Non-Mag Sub (NMDC)", "length": 9.1, "magnetic": False},
            {"name": "ВЗД (резерв)", "length": 8.5, "magnetic": True, "magnetic_moment": 15.0},
            {"name": "УЗС", "length": 8.9, "magnetic": True, "magnetic_moment": 8.0},
            {"name": "НУБТ", "length": 9.1, "magnetic": True, "magnetic_moment": 5.0},
        ],
        "total_length": 54.5,
        "sensor_positions": [
            {"name": "Инклинометр RSS", "offset_from_bit": 1.5, "in_nm_sub": False},
            {"name": "Инклинометр MWD", "offset_from_bit": 22.4, "in_nm_sub": True}
        ]
    },
    
    "КНБК с LWD (каротаж)": {
        "description": "КНБК с модулем каротажа во время бурения",
        "elements": [
            {"name": "Долото PDC", "length": 0.3, "magnetic": False},
            {"name": "ВЗД", "length": 8.5, "magnetic": True, "magnetic_moment": 15.0},
            {"name": "Non-Mag Sub (NMDC)", "length": 9.1, "magnetic": False},
            {"name": "MWD", "length": 6.0, "magnetic": False},
            {"name": "Non-Mag Sub (NMDC)", "length": 9.1, "magnetic": False},
            {"name": "LWD (Resistivity + Gamma)", "length": 9.5, "magnetic": False},
            {"name": "Non-Mag Sub (NMDC)", "length": 9.1, "magnetic": False},
            {"name": "УЗС", "length": 8.9, "magnetic": True, "magnetic_moment": 8.0},
            {"name": "НУБТ", "length": 9.1, "magnetic": True, "magnetic_moment": 5.0},
        ],
        "total_length": 69.6,
        "sensor_positions": [
            {"name": "Инклинометр MWD", "offset_from_bit": 23.9, "in_nm_sub": True},
            {"name": "Резистивиметр LWD", "offset_from_bit": 42.5, "in_nm_sub": True}
        ]
    }
}

# ============================================================================
# ФИЗИЧЕСКАЯ МОДЕЛЬ МАГНИТНЫХ ПОМЕХ
# ============================================================================

class MagneticInterferenceModel:
    """
    Расчет магнитного поля от ферромагнитных элементов КНБК
    
    Использует модель магнитного диполя:
    B = (μ₀ / 4π) * (3(m·r)r̂ - m) / r³
    
    Где:
    - B: вектор магнитной индукции, Тл
    - μ₀: магнитная постоянная = 4π × 10⁷ Тл·м/А
    - m: магнитный момент элемента, А·м²
    - r: расстояние от элемента до датчика, м
    """
    
    def __init__(self):
        self.mu_0 = 4 * math.pi * 1e-7  # Магнитная постоянная, Тл·м/А
        self.earth_field = 50e-6  # Геомагнитное поле, Тл (типично для ХМАО)
    
    def calculate_dipole_field(self, magnetic_moment_Am2: float, distance_m: float) -> float:
        """
        Расчет магнитного поля от диполя на расстоянии r
        
        B = (μ₀ / 4π) * m / r³
        """
        if distance_m <= 0:
            return float('inf')
        
        B = (self.mu_0 / (4 * math.pi)) * magnetic_moment_Am2 / (distance_m ** 3)
        return B  # Тесла
    
    def calculate_total_interference(self, bha_elements: List[Dict], 
                                    sensor_position_m: float) -> Dict:
        """
        Расчет суммарного магнитного поля от всех ферромагнитных элементов
        
        Args:
            bha_elements: список элементов КНБК
            sensor_position_m: позиция датчика от долота, м
        
        Returns:
            Dict с результатами расчета
        """
        total_field = 0.0
        contributions = []
        
        current_position = 0.0
        
        for element in bha_elements:
            element_center = current_position + element["length"] / 2
            distance = abs(sensor_position_m - element_center)
            
            if element.get("magnetic", False):
                m = element.get("magnetic_moment", 10.0)  # А·м²
                B = self.calculate_dipole_field(m, distance)
                total_field += B
                
                contributions.append({
                    "element": element["name"],
                    "distance_m": round(distance, 2),
                    "field_T": round(B * 1e6, 3),  # мкТл
                    "magnetic_moment": m
                })
            
            current_position += element["length"]
        
        # Отношение помехи к геомагнитному полю
        interference_ratio = (total_field / self.earth_field) * 100  # %
        
        # Влияние на точность азимута
        # ΔAzimuth ≈ arctan(B_interference / B_earth)
        azimuth_error_deg = math.degrees(math.atan2(total_field, self.earth_field))
        
        return {
            "total_interference_T": total_field,
            "total_interference_uT": round(total_field * 1e6, 3),
            "earth_field_uT": round(self.earth_field * 1e6, 2),
            "interference_ratio_percent": round(interference_ratio, 2),
            "azimuth_error_deg": round(azimuth_error_deg, 2),
            "contributions": contributions,
            "status": self._get_status(azimuth_error_deg, interference_ratio)
        }
    
    def _get_status(self, azimuth_error: float, interference_ratio: float) -> str:
        """Определение статуса магнитной обстановки"""
        if azimuth_error < 0.5 and interference_ratio < 10:
            return "🟢 ОТЛИЧНО"
        elif azimuth_error < 1.0 and interference_ratio < 20:
            return "🟢 НОРМА"
        elif azimuth_error < 2.0 and interference_ratio < 40:
            return " ПОВЫШЕННАЯ ПОМЕХА"
        elif azimuth_error < 5.0:
            return "🟠 ВЫСОКАЯ ПОМЕХА"
        else:
            return "🔴 КРИТИЧЕСКАЯ ПОМЕХА"


# ============================================================================
# ОПТИМИЗАТОР ПОЗИЦИОНИРОВАНИЯ ДАТЧИКОВ
# ============================================================================

class SensorPositionOptimizer:
    """
    Оптимизация позиции датчиков в окнах резистивиметра
    
    Критерии:
    1. Минимизация магнитных помех
    2. Нахождение в немагнитной секции (NMDC)
    3. Оптимальное расстояние от долота для качества измерений
    """
    
    def __init__(self):
        self.magnetic_model = MagneticInterferenceModel()
    
    def find_optimal_position(self, bha_elements: List[Dict], 
                             sensor_type: str = "inclination") -> Dict:
        """
        Поиск оптимальной позиции датчика
        
        Args:
            bha_elements: конфигурация КНБК
            sensor_type: тип датчика (inclination, resistivity, gamma)
        
        Returns:
            Dict с оптимальной позицией и рекомендациями
        """
        # Определяем немагнитные секции
        nm_sections = []
        current_pos = 0.0
        in_nm_section = False
        section_start = 0.0
        
        for element in bha_elements:
            if not element.get("magnetic", False) and element["length"] >= 3.0:
                if not in_nm_section:
                    section_start = current_pos
                    in_nm_section = True
            else:
                if in_nm_section:
                    nm_sections.append({
                        "start": section_start,
                        "end": current_pos,
                        "length": current_pos - section_start
                    })
                    in_nm_section = False
            
            current_pos += element["length"]
        
        if in_nm_section:
            nm_sections.append({
                "start": section_start,
                "end": current_pos,
                "length": current_pos - section_start
            })
        
        # Поиск оптимальной позиции в каждой немагнитной секции
        best_position = None
        min_interference = float('inf')
        
        for section in nm_sections:
            # Проверяем несколько точек в секции
            for offset in [0.3, 0.5, section["length"]/2, section["length"] - 0.5, section["length"] - 0.3]:
                test_pos = section["start"] + offset
                
                result = self.magnetic_model.calculate_total_interference(
                    bha_elements, test_pos
                )
                
                if result["total_interference_T"] < min_interference:
                    min_interference = result["total_interference_T"]
                    best_position = {
                        "position_m": round(test_pos, 2),
                        "in_nm_section": True,
                        "section_length": section["length"],
                        "interference": result
                    }
        
        if best_position is None:
            # Если немагнитных секций нет, ищем позицию с минимальной помехой
            for pos in np.arange(5, 50, 1):
                result = self.magnetic_model.calculate_total_interference(
                    bha_elements, pos
                )
                if result["total_interference_T"] < min_interference:
                    min_interference = result["total_interference_T"]
                    best_position = {
                        "position_m": round(pos, 2),
                        "in_nm_section": False,
                        "interference": result
                    }
        
        return best_position


# ============================================================================
# ИНТЕРФЕЙСНЫЕ КОМПОНЕНТЫ
# ============================================================================

def create_telemetry_system_layout():
    """Макет модуля телеметрических систем"""
    return html.Div([
        html.Div([
            html.H2("Телеметрические системы в КНБК", style={"color": "white", "margin": "0"}),
            html.P("Расчет магнитных помех, позиционирование датчиков, влияние на инклинометр", 
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "20px", "borderRadius": "8px", "marginBottom": "20px"}),
        
        # Выбор конфигурации
        dbc.Card([
            dbc.CardBody([
                html.H5("Выбор типовой конфигурации КНБК", style={"marginBottom": "15px"}),
                dcc.Dropdown(
                    id='ts-bha-config',
                    options=[{"label": k, "value": k} for k in TYPICAL_BHA_CONFIGS.keys()],
                    value="Вертикальное бурение с MWD",
                    clearable=False
                ),
                html.Div(id='ts-config-description', style={"marginTop": "10px", "fontSize": "13px", "color": "#64748B"})
            ])
        ], className="mb-4"),
        
        # Визуализация КНБК
        html.H4("Схема КНБК с позициями датчиков", style={"color": "#0F172A", "marginBottom": "10px"}),
        dcc.Graph(id='ts-bha-visualization', style={"height": "400px"}),
        
        # Анализ магнитных помех
        dbc.Row([
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="МАГНИТНАЯ ПОМЕХА"),
                    html.Div(id='ts-interference-value', className="metric-value", children="0.0 мкТл")
                ])
            ], width=4),
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="ОШИБКА АЗИМУТА"),
                    html.Div(id='ts-azimuth-error', className="metric-value", children="0.0°")
                ])
            ], width=4),
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="СТАТУС"),
                    html.Div(id='ts-magnetic-status', children="ОЖИДАНИЕ")
                ])
            ], width=4),
        ], className="mb-4"),
        
        # Рекомендации
        html.Div(id='ts-recommendations', className="mb-4"),
        
        # Таблица вкладок
        dcc.Tabs(id='ts-tabs', value='tab-analysis', children=[
            dcc.Tab(label='Анализ помех', value='tab-analysis'),
            dcc.Tab(label='Оптимизация позиции', value='tab-optimization'),
            dcc.Tab(label('Детализация', value='tab-details'),
        ]),
        
        html.Div(id='ts-tabs-content', style={"marginTop": "20px"}),
    ])


def create_analysis_tab():
    return html.Div([
        html.H4("Детальный анализ магнитных помех", style={"color": "#0F172A", "marginBottom": "15px"}),
        html.Div(id='ts-interference-breakdown'),
    ])


def create_optimization_tab():
    return html.Div([
        html.H4("Оптимизация позиции датчиков", style={"color": "#0F172A", "marginBottom": "15px"}),
        html.Div(id='ts-optimization-results'),
    ])


def create_details_tab():
    return html.Div([
        html.H4("Детализация конфигурации", style={"color": "#0F172A", "marginBottom": "15px"}),
        html.Div(id='ts-config-details'),
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def telemetry_system_callbacks(app, data_bridge):
    
    @app.callback(
        [Output('ts-config-description', 'children'),
         Output('ts-bha-visualization', 'figure'),
         Output('ts-interference-value', 'children'),
         Output('ts-azimuth-error', 'children'),
         Output('ts-magnetic-status', 'children'),
         Output('ts-recommendations', 'children')],
        Input('ts-bha-config', 'value')
    )
    def update_telemetry_analysis(config_name):
        if config_name not in TYPICAL_BHA_CONFIGS:
            return html.Div(), go.Figure(), "0.0 мкТл", "0.0°", "ОЖИДАНИЕ", html.Div()
        
        config = TYPICAL_BHA_CONFIGS[config_name]
        
        # Визуализация КНБК
        fig = go.Figure()
        
        current_pos = 0.0
        for i, element in enumerate(config["elements"]):
            color = "#EF4444" if element.get("magnetic", False) else "#3B82F6"
            fig.add_trace(go.Scatter(
                x=[current_pos, current_pos + element["length"]],
                y=[0, 0],
                mode='lines',
                line=dict(color=color, width=20),
                name=element["name"],
                showlegend=(i == 0)
            ))
            current_pos += element["length"]
        
        # Позиции датчиков
        for sensor in config["sensor_positions"]:
            fig.add_trace(go.Scatter(
                x=[sensor["offset_from_bit"]],
                y=[0],
                mode='markers',
                marker=dict(size=15, color="#10B981", symbol='star'),
                name=sensor["name"]
            ))
        
        fig.update_layout(
            title=f"Конфигурация: {config_name}",
            xaxis_title="Расстояние от долота, м",
            yaxis=dict(showticklabels=False),
            template="plotly_white",
            height=400
        )
        
        # Анализ магнитных помех для каждого датчика
        magnetic_model = MagneticInterferenceModel()
        optimizer = SensorPositionOptimizer()
        
        total_interference = 0.0
        max_azimuth_error = 0.0
        recommendations = []
        
        for sensor in config["sensor_positions"]:
            result = magnetic_model.calculate_total_interference(
                config["elements"], sensor["offset_from_bit"]
            )
            
            total_interference += result["total_interference_uT"]
            max_azimuth_error = max(max_azimuth_error, result["azimuth_error_deg"])
            
            if result["azimuth_error_deg"] > 1.0:
                recommendations.append(
                    f"⚠️ {sensor['name']}: ошибка азимута {result['azimuth_error_deg']:.2f}°"
                )
        
        # Оптимизация
        optimal = optimizer.find_optimal_position(config["elements"])
        if optimal:
            recommendations.append(
                f"✅ Оптимальная позиция датчика: {optimal['position_m']} м от долота"
            )
        
        return (
            config["description"],
            fig,
            f"{total_interference:.2f} мкТл",
            f"{max_azimuth_error:.2f}°",
            result["status"],
            html.Div([
                html.H6("Рекомендации:", style={"marginBottom": "10px"}),
                html.Ul([html.Li(rec) for rec in recommendations])
            ])
        )
    
    @app.callback(
        Output('ts-tabs-content', 'children'),
        Input('ts-tabs', 'value')
    )
    def render_ts_tab(tab):
        if tab == 'tab-analysis': return create_analysis_tab()
        if tab == 'tab-optimization': return create_optimization_tab()
        if tab == 'tab-details': return create_details_tab()
        return html.Div()
