"""
МОДУЛЬ КОНТРОЛЯ РЕЗИСТИВИМЕТРА (РЕЗАКА) С НЕСИММЕТРИЧНЫМИ ОКНАМИ
Защита от ошибок позиционирования, переворота инструмента,
неправильных замеров расстояний до окон.

Основан на:
- Практике NOV, Smith Services, Baker Hughes
- IADC Guidelines for MWD/LWD Tool Placement
- Опыт аварий из-за неправильного позиционирования датчиков
"""
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np

# ============================================================================
# БАЗА ДАННЫХ ТИПОВЫХ РЕЗИСТИВИМЕТРОВ
# ============================================================================

RESISTIVITY_SUBS_DB = {
    "NMDC-6.5 (Non-Mag Drill Collar 6.5")": {
        "length_m": 9.14,
        "od_mm": 165.1,
        "id_mm": 71.4,
        "windows": [
            {"name": "Окно 1 (верхнее)", "offset_from_top_m": 2.5, "length_m": 0.3},
            {"name": "Окно 2 (нижнее)", "offset_from_top_m": 6.8, "length_m": 0.3}
        ],
        "is_symmetric": False,
        "magnetic": False
    },
    
    "NMDC-8 (Non-Mag Drill Collar 8")": {
        "length_m": 9.14,
        "od_mm": 203.2,
        "id_mm": 71.4,
        "windows": [
            {"name": "Окно 1 (верхнее)", "offset_from_top_m": 2.0, "length_m": 0.3},
            {"name": "Окно 2 (нижнее)", "offset_from_top_m": 7.2, "length_m": 0.3}
        ],
        "is_symmetric": False,
        "magnetic": False
    },
    
    "NMDC-6.5 Symmetric": {
        "length_m": 9.14,
        "od_mm": 165.1,
        "id_mm": 71.4,
        "windows": [
            {"name": "Окно 1", "offset_from_top_m": 2.5, "length_m": 0.3},
            {"name": "Окно 2", "offset_from_top_m": 6.64, "length_m": 0.3}
        ],
        "is_symmetric": True,
        "magnetic": False
    }
}

# ============================================================================
# МОДЕЛЬ АНАЛИЗА РЕЗИСТИВИМЕТРА
# ============================================================================

@dataclass
class WindowMeasurement:
    """Измерение окна резистивиметра"""
    window_name: str
    distance_from_top_m: float  # Расстояние от верхнего торца
    distance_from_bottom_m: float  # Расстояние от нижнего торца
    measured_by: str  # Кто измерял
    timestamp: str  # Время измерения

class ResistivitySubAnalyzer:
    """
    Анализатор резистивиметра с защитой от ошибок позиционирования
    
    Проверяет:
    1. Симметрию измерений (расстояние от верха + от низа = длина инструмента)
    2. Правильность ориентации (не перевернут ли инструмент)
    3. Соответствие паспортным данным
    4. Влияние на телеметрию
    """
    
    def __init__(self, sub_type: str):
        if sub_type not in RESISTIVITY_SUBS_DB:
            raise ValueError(f"Неизвестный тип резистивиметра: {sub_type}")
        
        self.sub_data = RESISTIVITY_SUBS_DB[sub_type]
        self.length = self.sub_data["length_m"]
        self.windows = self.sub_data["windows"]
        self.is_symmetric = self.sub_data["is_symmetric"]
    
    def validate_measurements(self, measurements: List[WindowMeasurement]) -> Dict:
        """
        Валидация измерений окон
        
        Возвращает:
        - Статус валидации
        - Выявленные ошибки
        - Рекомендации
        """
        errors = []
        warnings = []
        validation_results = []
        
        for meas in measurements:
            # 1. Проверка суммы расстояний (должна равняться длине инструмента)
            total_distance = meas.distance_from_top_m + meas.distance_from_bottom_m
            deviation = abs(total_distance - self.length)
            
            if deviation > 0.05:  # Допуск 5 см
                errors.append({
                    "type": "LENGTH_MISMATCH",
                    "message": f"Сумма расстояний ({total_distance:.2f} м) не равна длине инструмента ({self.length} м). " +
                              f"Отклонение: {deviation:.3f} м",
                    "severity": "CRITICAL"
                })
            elif deviation > 0.02:
                warnings.append({
                    "type": "LENGTH_WARNING",
                    "message": f"Небольшое отклонение суммы расстояний: {deviation:.3f} м"
                })
            
            # 2. Проверка соответствия паспортным данным
            passport_window = next((w for w in self.windows if w["name"] in meas.window_name), None)
            
            if passport_window:
                expected_from_top = passport_window["offset_from_top_m"]
                deviation_from_passport = abs(meas.distance_from_top_m - expected_from_top)
                
                if deviation_from_passport > 0.1:  # Допуск 10 см
                    errors.append({
                        "type": "PASSPORT_MISMATCH",
                        "message": f"Измеренное расстояние до {meas.window_name} ({meas.distance_from_top_m:.2f} м) " +
                                  f"не соответствует паспорту ({expected_from_top} м). " +
                                  f"Отклонение: {deviation_from_passport:.3f} м",
                        "severity": "HIGH"
                    })
                
                validation_results.append({
                    "window": meas.window_name,
                    "measured_from_top": meas.distance_from_top_m,
                    "passport_from_top": expected_from_top,
                    "deviation": round(deviation_from_passport, 3),
                    "status": "OK" if deviation_from_passport < 0.05 else "WARNING"
                })
            
            # 3. Проверка на переворот инструмента
            # Если расстояние от верха близко к паспортному расстоянию от низа — возможен переворот
            expected_from_bottom = self.length - passport_window["offset_from_top_m"] if passport_window else None
            
            if expected_from_bottom and abs(meas.distance_from_top_m - expected_from_bottom) < 0.1:
                warnings.append({
                    "type": "POSSIBLE_INVERSION",
                    "message": f"⚠️ ВНИМАНИЕ: Измеренное расстояние до {meas.window_name} " +
                              f"({meas.distance_from_top_m:.2f} м) близко к паспортному расстоянию от НИЖНЕГО торца " +
                              f"({expected_from_bottom:.2f} м). Возможна неправильная ориентация инструмента!"
                })
        
        # 4. Проверка симметрии (если резак симметричный)
        if self.is_symmetric and len(measurements) >= 2:
            window1 = next((m for m in measurements if "1" in m.window_name or "верхн" in m.window_name.lower()), None)
            window2 = next((m for m in measurements if "2" in m.window_name or "нижн" in m.window_name.lower()), None)
            
            if window1 and window2:
                symmetry_deviation = abs(window1.distance_from_top_m - (self.length - window2.distance_from_top_m))
                if symmetry_deviation > 0.05:
                    errors.append({
                        "type": "SYMMETRY_VIOLATION",
                        "message": f"Нарушена симметрия окон: отклонение {symmetry_deviation:.3f} м"
                    })
        
        # Итоговый статус
        if errors:
            status = "FAILED"
        elif warnings:
            status = "WARNING"
        else:
            status = "PASSED"
        
        return {
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "validation_results": validation_results,
            "sub_type": self.sub_data,
            "recommendations": self._generate_recommendations(errors, warnings)
        }
    
    def calculate_sensor_position_impact(self, sensor_offset_from_bit: float, 
                                        window_position: float) -> Dict:
        """
        Расчет влияния неправильного позиционирования датчика на телеметрию
        
        Args:
            sensor_offset_from_bit: Расчетное положение датчика от долота, м
            window_position: Фактическое положение окна, м
        
        Returns:
            Dict с оценкой влияния на точность
        """
        position_error = abs(sensor_offset_from_bit - window_position)
        
        # Влияние на точность азимута (упрощенная модель)
        # Чем дальше датчик от расчетной позиции, тем больше магнитных помех
        azimuth_degradation = position_error * 0.5  # градусы на метр
        
        # Влияние на качество сигнала резистивиметра
        signal_quality = max(0, 100 - position_error * 20)  # %
        
        return {
            "position_error_m": round(position_error, 3),
            "azimuth_degradation_deg": round(azimuth_degradation, 2),
            "signal_quality_percent": round(signal_quality, 1),
            "status": "OK" if position_error < 0.1 else ("WARNING" if position_error < 0.3 else "CRITICAL")
        }
    
    def _generate_recommendations(self, errors: List, warnings: List) -> List[str]:
        """Генерация рекомендаций"""
        recs = []
        
        if any(e["type"] == "LENGTH_MISMATCH" for e in errors):
            recs.append("🚨 КРИТИЧНО: Повторно измерьте расстояния до окон. Проверьте правильность выбора торцов.")
        
        if any(e["type"] == "PASSPORT_MISMATCH" for e in errors):
            recs.append("⚠️ Сверьте измерения с паспортом инструмента. Возможно, используется другой тип резака.")
        
        if any(w["type"] == "POSSIBLE_INVERSION" for w in warnings):
            recs.append("️ ПРОВЕРЬТЕ ОРИЕНТАЦИЮ: Убедитесь, что инструмент не перевернут. Проверьте маркировку торцов.")
        
        if not errors and not warnings:
            recs.append("✅ Все измерения в норме. Инструмент готов к спуску.")
        
        return recs


# ============================================================================
# ЧЕК-ЛИСТ ПЕРЕД СПУСКОМ
# ============================================================================

RESISTIVITY_CHECKLIST = [
    {
        "id": "1.1",
        "action": "Измерить расстояние от ВЕРХНЕГО торца до центра Окна 1",
        "responsible": "Инженер MWD",
        "critical": True
    },
    {
        "id": "1.2",
        "action": "Измерить расстояние от НИЖНЕГО торца до центра Окна 1",
        "responsible": "Инженер MWD",
        "critical": True
    },
    {
        "id": "1.3",
        "action": "Проверить: сумма расстояний = длине инструмента (±5 см)",
        "responsible": "Инженер MWD",
        "critical": True
    },
    {
        "id": "2.1",
        "action": "Измерить расстояние от ВЕРХНЕГО торца до центра Окна 2",
        "responsible": "Инженер MWD",
        "critical": True
    },
    {
        "id": "2.2",
        "action": "Измерить расстояние от НИЖНЕГО торца до центра Окна 2",
        "responsible": "Инженер MWD",
        "critical": True
    },
    {
        "id": "2.3",
        "action": "Проверить: сумма расстояний = длине инструмента (±5 см)",
        "responsible": "Инженер MWD",
        "critical": True
    },
    {
        "id": "3.1",
        "action": "Сверить измерения с паспортом инструмента",
        "responsible": "Супервайзер",
        "critical": True
    },
    {
        "id": "3.2",
        "action": "Проверить маркировку торцов (верх/низ)",
        "responsible": "Супервайзер",
        "critical": True
    },
    {
        "id": "4.1",
        "action": "Зафиксировать результаты в журнале",
        "responsible": "Инженер MWD",
        "critical": False
    },
    {
        "id": "4.2",
        "action": "Сфотографировать инструмент с рулеткой",
        "responsible": "Инженер MWD",
        "critical": False
    }
]


# ============================================================================
# ИНТЕРФЕЙСНЫЕ КОМПОНЕНТЫ
# ============================================================================

def create_resistivity_control_layout():
    """Макет модуля контроля резистивиметра"""
    return html.Div([
        html.Div([
            html.H2("Контроль резистивиметра (резака)", style={"color": "white", "margin": "0"}),
            html.P("Защита от ошибок позиционирования, переворота инструмента, неправильных замеров", 
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "20px", "borderRadius": "8px", "marginBottom": "20px"}),
        
        # Выбор типа резака
        dbc.Card([
            dbc.CardBody([
                html.H5("Тип резистивиметра:", style={"marginBottom": "10px"}),
                dcc.Dropdown(
                    id='res-sub-type',
                    options=[{"label": k, "value": k} for k in RESISTIVITY_SUBS_DB.keys()],
                    value="NMDC-6.5 (Non-Mag Drill Collar 6.5\")",
                    clearable=False
                ),
                html.Div(id='res-sub-info', style={"marginTop": "10px", "fontSize": "13px", "color": "#64748B"})
            ])
        ], className="mb-4"),
        
        # Визуализация резака
        html.H4("Схема резистивиметра", style={"color": "#0F172A", "marginBottom": "10px"}),
        dcc.Graph(id='res-sub-visualization', style={"height": "300px"}),
        
        # Ввод измерений
        html.H4("Замеры окон", style={"color": "#0F172A", "marginBottom": "15px"}),
        dbc.Card([
            dbc.CardBody([
                html.H6("Окно 1 (верхнее):", style={"marginBottom": "10px"}),
                dbc.Row([
                    dbc.Col([
                        html.Label("Расстояние от ВЕРХНЕГО торца, м:", style={"fontSize": "12px"}),
                        dcc.Input(id='res-window1-from-top', type='number', value=2.5, min=0, max=10, step=0.01,
                                 style={"width": "100%", "padding": "5px"})
                    ], width=6),
                    dbc.Col([
                        html.Label("Расстояние от НИЖНЕГО торца, м:", style={"fontSize": "12px"}),
                        dcc.Input(id='res-window1-from-bottom', type='number', value=6.64, min=0, max=10, step=0.01,
                                 style={"width": "100%", "padding": "5px"})
                    ], width=6),
                ], className="mb-3"),
                
                html.H6("Окно 2 (нижнее):", style={"marginBottom": "10px", "marginTop": "15px"}),
                dbc.Row([
                    dbc.Col([
                        html.Label("Расстояние от ВЕРХНЕГО торца, м:", style={"fontSize": "12px"}),
                        dcc.Input(id='res-window2-from-top', type='number', value=6.8, min=0, max=10, step=0.01,
                                 style={"width": "100%", "padding": "5px"})
                    ], width=6),
                    dbc.Col([
                        html.Label("Расстояние от НИЖНЕГО торца, м:", style={"fontSize": "12px"}),
                        dcc.Input(id='res-window2-from-bottom', type='number', value=2.34, min=0, max=10, step=0.01,
                                 style={"width": "100%", "padding": "5px"})
                    ], width=6),
                ], className="mb-3"),
                
                dbc.Button("Проверить измерения", id='btn-validate-resistivity', color="primary", className="w-100"),
            ])
        ], className="mb-4"),
        
        # Результаты валидации
        html.Div(id='res-validation-results', className="mb-4"),
        
        # Чек-лист
        html.H4("Чек-лист перед спуском", style={"color": "#0F172A", "marginBottom": "15px"}),
        html.Div(id='res-checklist'),
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def resistivity_control_callbacks(app, data_bridge):
    
    @app.callback(
        [Output('res-sub-info', 'children'),
         Output('res-sub-visualization', 'figure')],
        Input('res-sub-type', 'value')
    )
    def update_sub_info(sub_type):
        if sub_type not in RESISTIVITY_SUBS_DB:
            return html.Div(), go.Figure()
        
        sub_data = RESISTIVITY_SUBS_DB[sub_type]
        
        info = html.Div([
            html.P(f"Длина: {sub_data['length_m']} м | OD: {sub_data['od_mm']} мм | ID: {sub_data['id_mm']} мм"),
            html.P(f"Симметричный: {'Да' if sub_data['is_symmetric'] else 'Нет'}"),
            html.P(f"Количество окон: {len(sub_data['windows'])}")
        ])
        
        # Визуализация
        fig = go.Figure()
        
        # Основной корпус
        fig.add_trace(go.Scatter(
            x=[0, sub_data['length_m']],
            y=[0, 0],
            mode='lines',
            line=dict(color="#3B82F6", width=30),
            name="Корпус"
        ))
        
        # Окна
        for i, window in enumerate(sub_data['windows']):
            fig.add_trace(go.Scatter(
                x=[window['offset_from_top_m'], window['offset_from_top_m'] + window['length_m']],
                y=[0, 0],
                mode='lines',
                line=dict(color="#EF4444", width=20),
                name=window['name']
            ))
            
            # Подписи
            fig.add_annotation(
                x=window['offset_from_top_m'] + window['length_m']/2,
                y=0.5,
                text=f"{window['name']}\n{window['offset_from_top_m']}м",
                showarrow=False,
                font=dict(size=10)
            )
        
        # Торцы
        fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(size=15, color="#10B981"), name="Верхний торец"))
        fig.add_trace(go.Scatter(x=[sub_data['length_m']], y=[0], mode='markers', marker=dict(size=15, color="#F59E0B"), name="Нижний торец"))
        
        fig.update_layout(
            title=f"Схема: {sub_type}",
            xaxis_title="Расстояние от верхнего торца, м",
            yaxis=dict(showticklabels=False),
            template="plotly_white",
            height=300
        )
        
        return info, fig
    
    @app.callback(
        Output('res-validation-results', 'children'),
        Input('btn-validate-resistivity', 'n_clicks'),
        [State('res-sub-type', 'value'),
         State('res-window1-from-top', 'value'),
         State('res-window1-from-bottom', 'value'),
         State('res-window2-from-top', 'value'),
         State('res-window2-from-bottom', 'value')],
        prevent_initial_call=True
    )
    def validate_resistivity(n_clicks, sub_type, w1_top, w1_bottom, w2_top, w2_bottom):
        if None in [w1_top, w1_bottom, w2_top, w2_bottom]:
            return html.Div("Заполните все поля", style={"color": "#dc2626"})
        
        analyzer = ResistivitySubAnalyzer(sub_type)
        
        measurements = [
            WindowMeasurement("Окно 1 (верхнее)", w1_top, w1_bottom, "Инженер", "2026-09-17"),
            WindowMeasurement("Окно 2 (нижнее)", w2_top, w2_bottom, "Инженер", "2026-09-17")
        ]
        
        result = analyzer.validate_measurements(measurements)
        
        # Отображение результатов
        status_colors = {
            "PASSED": "#10B981",
            "WARNING": "#F59E0B",
            "FAILED": "#EF4444"
        }
        
        status_texts = {
            "PASSED": "✅ ПРОЙДЕНО",
            "WARNING": "⚠️ ТРЕБУЕТ ВНИМАНИЯ",
            "FAILED": "🚨 НЕ ПРОЙДЕНО"
        }
        
        color = status_colors.get(result["status"], "#64748B")
        
        return html.Div([
            html.Div(style={
                "backgroundColor": "#111827", "padding": "20px", "borderRadius": "8px",
                "textAlign": "center", "border": f"3px solid {color}", "marginBottom": "15px"
            }, children=[
                html.Div("РЕЗУЛЬТАТ ПРОВЕРКИ", style={"color": "#9CA3AF", "fontSize": "13px"}),
                html.Div(status_texts.get(result["status"], "НЕИЗВЕСТНО"), 
                        style={"color": color, "fontSize": "24px", "fontWeight": "bold"}),
            ]),
            
            # Ошибки
            html.Div([
                html.H6("Ошибки:", style={"color": "#EF4444", "marginBottom": "10px"}),
                html.Ul([html.Li(f"{e['message']}", style={"marginBottom": "5px"}) for e in result["errors"]])
            ] if result["errors"] else html.Div(), style={"padding": "10px", "backgroundColor": "#FEE2E2", "borderRadius": "6px", "marginBottom": "10px"}),
            
            # Предупреждения
            html.Div([
                html.H6("Предупреждения:", style={"color": "#F59E0B", "marginBottom": "10px"}),
                html.Ul([html.Li(f"{w['message']}", style={"marginBottom": "5px"}) for w in result["warnings"]])
            ] if result["warnings"] else html.Div(), style={"padding": "10px", "backgroundColor": "#FEF3C7", "borderRadius": "6px", "marginBottom": "10px"}),
            
            # Рекомендации
            html.Div([
                html.H6("Рекомендации:", style={"marginBottom": "10px"}),
                html.Ul([html.Li(rec, style={"marginBottom": "5px"}) for rec in result["recommendations"]])
            ], style={"padding": "10px", "backgroundColor": "#F0FDF4", "borderRadius": "6px"}),
        ])
    
    @app.callback(
        Output('res-checklist', 'children'),
        Input('res-sub-type', 'value')
    )
    def render_checklist(sub_type):
        return html.Div([
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("№"),
                    html.Th("Действие"),
                    html.Th("Ответственный"),
                    html.Th("Критично"),
                    html.Th("Статус")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(item["id"]),
                        html.Td(item["action"]),
                        html.Td(item["responsible"]),
                        html.Td("Да" if item["critical"] else "Нет", 
                               style={"color": "#EF4444" if item["critical"] else "#10B981"}),
                        html.Td(dcc.Checklist(options=[{"label": "", "value": "done"}], value=[]))
                    ]) for item in RESISTIVITY_CHECKLIST
                ])
            ], bordered=True, hover=True, responsive=True, size="sm")
        ])
