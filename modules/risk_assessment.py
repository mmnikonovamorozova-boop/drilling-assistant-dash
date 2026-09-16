"""
МОДУЛЬ ОЦЕНКИ РИСКОВ С УЧЕТОМ ППБ, ГЕОЛОГИИ И КЛИМАТА
Анализ рисков при спуске несбалансированной КНБК, учет климатических 
коэффициентов (Зима/Зап. Сибирь) и интеграция с данными о растворе
"""
import math
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go


# ============================================================================
# БАЗА ДАННЫХ КЛИМАТИЧЕСКИХ И ГЕОЛОГИЧЕСКИХ КОЭФФИЦИЕНТОВ
# ============================================================================

CLIMATE_COEFFICIENTS = {
    "Лето / Юг России": {
        "k_holod": 1.0,  # Коэффициент хладноломкости
        "k_viscosity": 1.0,  # Коэффициент загустевания раствора
        "k_steel": 1.0,  # Поправка на прочность стали
        "description": "Стандартные условия"
    },
    "Зима / Западная Сибирь": {
        "k_holod": 1.15,  # Повышенная хрупкость стали при T < -20°C
        "k_viscosity": 1.3,  # Загустевание раствора на морозе
        "k_steel": 0.9,  # Снижение ударной вязкости
        "description": "T до -40°C, риск хладноломкости"
    },
    "Зима / Ямал": {
        "k_holod": 1.25,
        "k_viscosity": 1.5,
        "k_steel": 0.85,
        "description": "Экстремальные условия, T до -50°C"
    },
    "Восточная Сибирь": {
        "k_holod": 1.20,
        "k_viscosity": 1.4,
        "k_steel": 0.88,
        "description": "T до -45°C, вечная мерзлота"
    }
}

LITHOLOGY_RISKS = {
    "Песчаник": {
        "abrasion_factor": 1.5,  # Высокий абразив
        "vibration_risk": "LOW",
        "recommendation": "Контролировать износ ВЗД, усилить очистку"
    },
    "Аргиллит": {
        "abrasion_factor": 0.8,
        "vibration_risk": "MEDIUM",
        "recommendation": "Риск сальникообразования, контролировать реологию"
    },
    "Известняк": {
        "abrasion_factor": 1.2,
        "vibration_risk": "HIGH",
        "recommendation": "Повышенная вибрация, снизить WOB"
    },
    "Глины": {
        "abrasion_factor": 0.5,
        "vibration_risk": "LOW",
        "recommendation": "Риск налипания, увеличить расход"
    },
    "Ангидрит": {
        "abrasion_factor": 1.8,
        "vibration_risk": "MEDIUM",
        "recommendation": "Критический абразив, минимизировать время работы"
    }
}


@dataclass
class PPBData:
    """Данные из План-Программы бурения"""
    interval_top: float  # Верх интервала, м
    interval_bottom: float  # Низ интервала, м
    lithology: str  # Литология
    planned_wob: float  # Проектная WOB, т
    planned_rpm: float  # Проектные обороты
    planned_flow: float  # Проектный расход, л/с
    mud_type: str  # Тип раствора
    mud_density: float  # Плотность, г/см³
    expected_temp: float  # Ожидаемая температура, °C
    dls_limit: float  # Ограничение по DLS, град/10м


class RiskCalculator:
    """Калькулятор рисков при спуске и бурении"""
    
    def __init__(self, ppb_data: PPBData, climate_zone: str, bha_elements: List[Dict]):
        self.ppb = ppb_data
        self.climate = CLIMATE_COEFFICIENTS.get(climate_zone, CLIMATE_COEFFICIENTS["Лето / Юг России"])
        self.bha_elements = bha_elements
        self.risks = []
    
    def calculate_surge_swab(self) -> Dict[str, float]:
        """
        Расчет гидравлических ударов (Surge/Swab) при спуске/подъеме
        Упрощенная модель по API RP 13D
        """
        # Параметры для расчета
        clearance_ratio = self._calculate_clearance_ratio()
        mud_pv = 25.0  # Пластическая вязкость (взять из DataBridge)
        mud_yp = 12.0  # ДНС
        
        # Скорость спуска (типичная)
        trip_speed = 0.3  # м/с
        
        # Расчет surge pressure (Па)
        surge_pressure = (
            (mud_pv * trip_speed / (clearance_ratio ** 2)) +
            (mud_yp * 0.5 / clearance_ratio)
        ) * self.climate["k_viscosity"]
        
        # Перевод в эквивалент плотности
        hydrostatic_head = (self.ppb.interval_bottom - self.ppb.interval_top) * 9.81
        surge_ecd = surge_pressure / (hydrostatic_head + 1e-6) / 1000
        
        return {
            "surge_pressure_pa": surge_pressure,
            "surge_ecd": self.ppb.mud_density + surge_ecd,
            "swab_ecd": self.ppb.mud_density - surge_ecd * 0.7,
            "clearance_ratio": clearance_ratio
        }
    
    def _calculate_clearance_ratio(self) -> float:
        """Расчет коэффициента зазора между КНБК и стенкой скважины"""
        if not self.bha_elements:
            return 0.3  # Дефолтное значение
        
        # Находим максимальный диаметр в КНБК
        max_od = max(el.get('od', 0) for el in self.bha_elements)
        hole_diameter = 215.9  # Типичный диаметр скважины, мм
        
        clearance = (hole_diameter - max_od) / hole_diameter
        return max(0.1, clearance)  # Минимум 10% зазора
    
    def calculate_cold_fracture_risk(self) -> Dict:
        """Оценка риска хладноломкости стали"""
        k_holod = self.climate["k_holod"]
        k_steel = self.climate["k_steel"]
        
        # Если зима и T < -20°C, повышенный риск
        if self.ppb.expected_temp < -20:
            risk_level = "HIGH"
            risk_score = 0.8 * k_holod
            recommendation = (
                "КРИТИЧЕСКИ: При T < -20°C использовать только стали группы S-135. "
                "Избегать ударных нагрузок при СПО. Прогреть инструмент перед спуском."
            )
        elif self.ppb.expected_temp < -10:
            risk_level = "MEDIUM"
            risk_score = 0.5 * k_holod
            recommendation = "Повышенный риск хладноломкости. Контролировать скорость спуска."
        else:
            risk_level = "LOW"
            risk_score = 0.2
            recommendation = "Температурные условия в норме"
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "recommendation": recommendation,
            "k_holod": k_holod,
            "k_steel": k_steel
        }
    
    def calculate_lithology_risk(self) -> Dict:
        """Оценка рисков по литологии"""
        litho_data = LITHOLOGY_RISKS.get(self.ppb.lithology, LITHOLOGY_RISKS["Песчаник"])
        
        # Корректировка на климат
        adjusted_abrasion = litho_data["abrasion_factor"] * self.climate["k_viscosity"]
        
        return {
            "lithology": self.ppb.lithology,
            "abrasion_risk": adjusted_abrasion,
            "vibration_risk": litho_data["vibration_risk"],
            "recommendation": litho_data["recommendation"]
        }
    
    def calculate_bha_balance_risk(self) -> Dict:
        """Оценка сбалансированности КНБК"""
        if len(self.bha_elements) < 2:
            return {"risk": "LOW", "score": 0.2, "message": "Недостаточно данных"}
        
        # Анализируем перепады диаметров
        max_delta_d = 0
        for i in range(len(self.bha_elements) - 1):
            od1 = self.bha_elements[i].get('od', 0)
            od2 = self.bha_elements[i+1].get('od', 0)
            delta = abs(od1 - od2)
            max_delta_d = max(max_delta_d, delta)
        
        if max_delta_d > 15:
            risk = "HIGH"
            score = 0.9
            message = f"Критический перепад {max_delta_d:.1f} мм — высокий риск уступа при СПО"
        elif max_delta_d > 10:
            risk = "MEDIUM"
            score = 0.6
            message = f"Повышенный перепад {max_delta_d:.1f} мм — контролировать скорость спуска"
        else:
            risk = "LOW"
            score = 0.2
            message = f"Перепады в норме (макс {max_delta_d:.1f} мм)"
        
        return {
            "risk": risk,
            "score": score,
            "max_delta_d": max_delta_d,
            "message": message
        }
    
    def calculate_total_risk(self) -> Dict:
        """Интегральная оценка риска рейса"""
        surge = self.calculate_surge_swab()
        cold = self.calculate_cold_fracture_risk()
        litho = self.calculate_lithology_risk()
        balance = self.calculate_bha_balance_risk()
        
        # Интегральный индекс риска (0-100%)
        total_risk = (
            cold["risk_score"] * 30 +
            balance["score"] * 40 +
            min(1.0, litho["abrasion_risk"] / 2.0) * 20 +
            (0.3 if surge["surge_ecd"] > self.ppb.mud_density + 0.05 else 0.1) * 10
        )
        
        total_risk = min(100, total_risk)
        
        if total_risk > 75:
            status = "CRITICAL"
            color = "#DC2626"
            action = "Не рекомендуется спуск. Требуется оптимизация КНБК."
        elif total_risk > 50:
            status = "WARNING"
            color = "#F59E0B"
            action = "Требуется повышенный контроль параметров."
        else:
            status = "ACCEPTABLE"
            color = "#10B981"
            action = "Риски в допустимых пределах."
        
        return {
            "total_risk": total_risk,
            "status": status,
            "color": color,
            "action": action,
            "components": {
                "surge_swab": surge,
                "cold_fracture": cold,
                "lithology": litho,
                "bha_balance": balance
            }
        }


def create_risk_assessment_panel():
    """Создает панель оценки рисков"""
    return html.Div([
        html.H4("Оценка рисков с учетом ППБ и климата", 
                style={"color": "#0f172a", "marginBottom": "15px"}),
        
        # Загрузка ППБ
        dbc.Card([
            dbc.CardHeader(html.H5("Загрузка данных из План-Программы бурения", style={"margin": "0"})),
            dbc.CardBody([
                dcc.Upload(
                    id='ppb-upload',
                    children=html.Div([
                        '📄 Перетащите файл ППБ (.xlsx) или ',
                        html.A('введите параметры вручную', style={"color": "#2563eb"})
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '2px',
                        'borderStyle': 'dashed',
                        'borderRadius': '8px',
                        'textAlign': 'center',
                        'backgroundColor': '#f8fafc'
                    },
                    multiple=False
                ),
                html.Div(id='ppb-upload-status', style={"marginTop": "10px"}),
            ])
        ], className="mb-3"),
        
        # Ручной ввод параметров ППБ
        dbc.Card([
            dbc.CardHeader(html.H5("Параметры интервала бурения", style={"margin": "0"})),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Климатическая зона:", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id='risk-climate-zone',
                            options=[{"label": k, "value": k} for k in CLIMATE_COEFFICIENTS.keys()],
                            value="Зима / Западная Сибирь",
                            clearable=False
                        ),
                    ], width=4),
                    
                    dbc.Col([
                        html.Label("Литология:", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id='risk-lithology',
                            options=[{"label": k, "value": k} for k in LITHOLOGY_RISKS.keys()],
                            value="Песчаник",
                            clearable=False
                        ),
                    ], width=4),
                    
                    dbc.Col([
                        html.Label("Интервал бурения (верх-низ), м:", style={"fontWeight": "bold"}),
                        dbc.Row([
                            dbc.Col(dcc.Input(id='risk-interval-top', type='number', value=2500, 
                                            min=0, max=10000, step=10, style={"width": "100%"})),
                            dbc.Col(html.Div("—", style={"textAlign": "center", "paddingTop": "8px"})),
                            dbc.Col(dcc.Input(id='risk-interval-bottom', type='number', value=2800,
                                             min=0, max=10000, step=10, style={"width": "100%"})),
                        ])
                    ], width=4),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Проектная WOB, т:", style={"fontWeight": "bold"}),
                        dcc.Input(id='risk-planned-wob', type='number', value=12.0,
                                 min=0, max=35, step=0.5, style={"width": "100%"})
                    ], width=3),
                    
                    dbc.Col([
                        html.Label("Проектный расход, л/с:", style={"fontWeight": "bold"}),
                        dcc.Input(id='risk-planned-flow', type='number', value=28.0,
                                 min=0, max=60, step=1, style={"width": "100%"})
                    ], width=3),
                    
                    dbc.Col([
                        html.Label("Плотность раствора, г/см³:", style={"fontWeight": "bold"}),
                        dcc.Input(id='risk-mud-density', type='number', value=1.12,
                                 min=0.8, max=2.5, step=0.01, style={"width": "100%"})
                    ], width=3),
                    
                    dbc.Col([
                        html.Label("Ожидаемая забойная T, °C:", style={"fontWeight": "bold"}),
                        dcc.Input(id='risk-expected-temp', type='number', value=90,
                                 min=-50, max=200, step=5, style={"width": "100%"})
                    ], width=3),
                ]),
            ])
        ], className="mb-3"),
        
        # Результаты оценки рисков
        html.Div(id='risk-assessment-results', style={"marginTop": "20px"}),
    ])


def create_risk_visualization(risk_data: Dict) -> go.Figure:
    """Создает визуализацию рисков"""
    fig = go.Figure()
    
    # Круговая диаграмма компонентов риска
    components = risk_data["components"]
    
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=risk_data["total_risk"],
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "ИНТЕГРАЛЬНЫЙ РИСК РЕЙСА", 'font': {'size': 18}},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': risk_data["color"]},
            'steps': [
                {'range': [0, 50], 'color': '#D1FAE5'},
                {'range': [50, 75], 'color': '#FEF3C7'},
                {'range': [75, 100], 'color': '#FEE2E2'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 75
            }
        }
    ))
    
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="#f8fafc"
    )
    
    return fig


def risk_assessment_callbacks(app, data_bridge):
    """Регистрирует callback'ы для модуля оценки рисков"""
    
    @app.callback(
        Output('risk-assessment-results', 'children'),
        [Input('risk-climate-zone', 'value'),
         Input('risk-lithology', 'value'),
         Input('risk-interval-top', 'value'),
         Input('risk-interval-bottom', 'value'),
         Input('risk-planned-wob', 'value'),
         Input('risk-planned-flow', 'value'),
         Input('risk-mud-density', 'value'),
         Input('risk-expected-temp', 'value')]
    )
    def calculate_and_display_risks(climate_zone, lithology, interval_top, interval_bottom,
                                   planned_wob, planned_flow, mud_density, expected_temp):
        # Защита от None
        if None in [interval_top, interval_bottom, planned_wob]:
            return html.P("Введите все параметры для расчета рисков")
        
        # Создаем PPB данные
        ppb_data = PPBData(
            interval_top=interval_top,
            interval_bottom=interval_bottom,
            lithology=lithology,
            planned_wob=planned_wob,
            planned_rpm=120.0,  # Дефолт
            planned_flow=planned_flow,
            mud_type="Полимерный",  # Взять из DataBridge
            mud_density=mud_density,
            expected_temp=expected_temp,
            dls_limit=2.0  # Дефолт
        )
        
        # Пример данных КНБК (в реальности брать из DataBridge)
        bha_elements = [
            {"name": "ТБТ-172", "od": 172.0},
            {"name": "Переводник", "od": 172.0},
            {"name": "ВЗД-172", "od": 172.0},
            {"name": "НУБТ-165", "od": 165.0},
        ]
        
        # Расчет рисков
        calculator = RiskCalculator(ppb_data, climate_zone, bha_elements)
        risk_result = calculator.calculate_total_risk()
        
        # Визуализация
        fig = create_risk_visualization(risk_result)
        
        # Формирование отчета
        components = risk_result["components"]
        
        return html.Div([
            # Индикатор общего риска
            dcc.Graph(figure=fig, config={'displayModeBar': False}),
            
            # Детализация по компонентам
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H6("🌡 Климатические риски", style={"color": "#0f172a"}),
                        html.P(f"Зона: {climate_zone}", style={"fontSize": "13px"}),
                        html.P(f"K хладноломкости: {components['cold_fracture']['k_holod']:.2f}", 
                              style={"fontSize": "13px"}),
                        html.P(components['cold_fracture']['recommendation'],
                              style={"fontSize": "12px", "color": components['cold_fracture']['risk_score'] > 0.5 and "#dc2626" or "#16a34a"}),
                    ], style={"padding": "15px", "backgroundColor": "#f8fafc", "borderRadius": "6px"})
                ], width=6),
                
                dbc.Col([
                    html.Div([
                        html.H6("⚖ Сбалансированность КНБК", style={"color": "#0f172a"}),
                        html.P(components['bha_balance']['message'], 
                              style={"fontSize": "13px", "color": components['bha_balance']['score'] > 0.5 and "#dc2626" or "#16a34a"}),
                        html.P(f"Макс перепад: {components['bha_balance'].get('max_delta_d', 0):.1f} мм",
                              style={"fontSize": "13px"}),
                    ], style={"padding": "15px", "backgroundColor": "#f8fafc", "borderRadius": "6px"})
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H6("🪨 Литология", style={"color": "#0f172a"}),
                        html.P(f"Абразивность: {components['lithology']['abrasion_risk']:.2f}", 
                              style={"fontSize": "13px"}),
                        html.P(components['lithology']['recommendation'],
                              style={"fontSize": "12px"}),
                    ], style={"padding": "15px", "backgroundColor": "#f8fafc", "borderRadius": "6px"})
                ], width=6),
                
                dbc.Col([
                    html.Div([
                        html.H6("💧 Surge/Swab эффекты", style={"color": "#0f172a"}),
                        html.P(f"Surge ECD: {components['surge_swab']['surge_ecd']:.3f} г/см³",
                              style={"fontSize": "13px"}),
                        html.P(f"Swab ECD: {components['surge_swab']['swab_ecd']:.3f} г/см³",
                              style={"fontSize": "13px"}),
                        html.P("Контролировать скорость СПО", style={"fontSize": "12px"}),
                    ], style={"padding": "15px", "backgroundColor": "#f8fafc", "borderRadius": "6px"})
                ], width=6),
            ]),
            
            # Итоговая рекомендация
            html.Div([
                html.H5("ИТОГОВАЯ РЕКОМЕНДАЦИЯ:", style={"color": risk_result["color"], "marginBottom": "10px"}),
                html.P(risk_result["action"], style={"fontSize": "14px", "fontWeight": "bold"}),
            ], style={
                "padding": "20px",
                "backgroundColor": risk_result["color"] + "20",  # 20 = прозрачность
                "border": f"2px solid {risk_result['color']}",
                "borderRadius": "8px",
                "marginTop": "20px"
            })
        ])
