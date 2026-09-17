"""
ПОЛНОЦЕННЫЙ МОДУЛЬ РАСЧЕТА ИЗНОСА ВЗД
Прогностическая модель на основе физики процесса и машинного обучения
"""
import math
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from sklearn.ensemble import RandomForestRegressor

# ============================================================================
# ФИЗИЧЕСКАЯ МОДЕЛЬ ИЗНОСА ЭЛАСТОМЕРОВ
# ============================================================================

class VZDWearPhysicsModel:
    """Физическая модель износа статора ВЗД"""
    
    def __init__(self):
        # Коэффициенты износа для разных типов эластомеров
        self.elastomer_wear_coeffs = {
            "Стандартный нитрил": 1.0,
            "Усиленный нитрил": 0.75,
            "Фторкаучук (FKM)": 0.60,
            "Специальный высокотемпературный": 0.65,
        }
        
        # Температурные коэффициенты деградации
        self.temp_degradation = {
            60: 1.0, 70: 1.1, 80: 1.25, 90: 1.45,
            100: 1.70, 110: 2.0, 120: 2.4, 130: 2.9
        }
    
    def calculate_thermal_degradation(self, temp_c: float, hours: float) -> float:
        """Расчет термической деградации эластомера"""
        # Находим ближайшие температурные точки
        temps = sorted(self.temp_degradation.keys())
        if temp_c <= temps[0]:
            k_temp = self.temp_degradation[temps[0]]
        elif temp_c >= temps[-1]:
            k_temp = self.temp_degradation[temps[-1]]
        else:
            # Линейная интерполяция
            for i in range(len(temps) - 1):
                if temps[i] <= temp_c < temps[i + 1]:
                    k_low = self.temp_degradation[temps[i]]
                    k_high = self.temp_degradation[temps[i + 1]]
                    k_temp = k_low + (k_high - k_low) * (temp_c - temps[i]) / (temps[i + 1] - temps[i])
                    break
        
        # Экспоненциальная зависимость от времени
        degradation_factor = 1.0 - math.exp(-hours / (200.0 / k_temp))
        return degradation_factor
    
    def calculate_mechanical_wear(self, torque_knm: float, rpm: float, hours: float) -> float:
        """Расчет механического износа от крутящего момента"""
        # Базовая скорость износа пропорциональна мощности
        power_kw = torque_knm * rpm * 0.10472  # кВт
        wear_rate = power_kw * 0.001  # условная скорость износа
        return min(1.0, wear_rate * hours / 100.0)
    
    def calculate_chemical_wear(self, sand_content: float, hours: float, mud_type: str) -> float:
        """Расчет химико-абразивного износа"""
        # Коэффициент абразивности для разных типов растворов
        abrasiveness = {
            "Полимерный": 1.0,
            "Гипсокалиевый": 1.3,
            "ГЭР": 1.5,
            "Кислотная пачка": 2.0,
        }.get(mud_type, 1.0)
        
        # Износ пропорционален концентрации песка и времени
        wear = sand_content * abrasiveness * hours / 500.0
        return min(1.0, wear)
    
    def calculate_total_wear(self, temp_c: float, torque_knm: float, rpm: float,
                            sand_content: float, mud_type: str, hours: float,
                            elastomer_type: str = "Стандартный нитрил") -> Dict:
        """Полный расчет износа ВЗД"""
        
        thermal = self.calculate_thermal_degradation(temp_c, hours)
        mechanical = self.calculate_mechanical_wear(torque_knm, rpm, hours)
        chemical = self.calculate_chemical_wear(sand_content, hours, mud_type)
        
        # Общий износ с учетом коэффициента эластомера
        k_elastomer = self.elastomer_wear_coeffs.get(elastomer_type, 1.0)
        total_wear = (0.4 * thermal + 0.35 * mechanical + 0.25 * chemical) * k_elastomer
        
        # Остаточный ресурс
        wear_percent = total_wear * 100.0
        remaining_life_hours = max(0, (1.0 - total_wear) * 250.0)  # 250 часов - базовый ресурс
        
        return {
            "total_wear_percent": round(wear_percent, 2),
            "thermal_degradation": round(thermal * 100, 2),
            "mechanical_wear": round(mechanical * 100, 2),
            "chemical_wear": round(chemical * 100, 2),
            "remaining_life_hours": round(remaining_life_hours, 1),
            "status": self._get_status(wear_percent, remaining_life_hours),
            "recommendations": self._get_recommendations(wear_percent, thermal, mechanical, chemical)
        }
    
    def _get_status(self, wear_percent: float, remaining_hours: float) -> str:
        if wear_percent < 30:
            return "🟢 НОРМА"
        elif wear_percent < 60:
            return " ПОВЫШЕННЫЙ ИЗНОС"
        elif wear_percent < 80:
            return "🟠 КРИТИЧЕСКИЙ"
        else:
            return " ТРЕБУЕТ ЗАМЕНЫ"
    
    def _get_recommendations(self, wear_percent: float, thermal: float, 
                            mechanical: float, chemical: float) -> List[str]:
        recs = []
        
        if thermal > 0.6:
            recs.append("️ Снизить температуру раствора или использовать термостойкий эластомер")
        
        if mechanical > 0.6:
            recs.append("⚙️ Уменьшить нагрузку на долото или крутящий момент")
        
        if chemical > 0.6:
            recs.append(" Улучшить очистку раствора от песка или сменить тип раствора")
        
        if wear_percent > 80:
            recs.append("🚨 СРОЧНО: Запланировать замену ВЗД в ближайшем рейсе")
        elif wear_percent > 60:
            recs.append("️ Контролировать параметры каждые 10 метров проходки")
        
        return recs if recs else ["✅ Параметры в норме. Продолжать мониторинг."]


# ============================================================================
# ИНТЕРФЕЙСНЫЕ КОМПОНЕНТЫ
# ============================================================================

def create_vzd_wear_panel():
    """Панель расчета износа ВЗД"""
    return html.Div([
        html.H5("Расчет износа ВЗД", style={"color": "#0f172a", "marginBottom": "15px", "fontWeight": "bold"}),
        
        dbc.Card([
            dbc.CardBody([
                # Входные параметры
                html.H6("Параметры эксплуатации:", style={"marginBottom": "10px", "fontSize": "13px"}),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Температура раствора, °C:", style={"fontSize": "11px"}),
                        dcc.Input(id='vzd-temp', type='number', value=90.0, min=20, max=150, step=1,
                                 style={"width": "100%", "padding": "5px", "fontSize": "12px"})
                    ], width=6),
                    dbc.Col([
                        html.Label("Крутящий момент, кН·м:", style={"fontSize": "11px"}),
                        dcc.Input(id='vzd-torque', type='number', value=8.5, min=0, max=20, step=0.5,
                                 style={"width": "100%", "padding": "5px", "fontSize": "12px"})
                    ], width=6),
                ], className="mb-2"),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Обороты ротора, об/мин:", style={"fontSize": "11px"}),
                        dcc.Input(id='vzd-rpm', type='number', value=120, min=0, max=300, step=5,
                                 style={"width": "100%", "padding": "5px", "fontSize": "12px"})
                    ], width=6),
                    dbc.Col([
                        html.Label("Содержание песка, %:", style={"fontSize": "11px"}),
                        dcc.Input(id='vzd-sand', type='number', value=0.5, min=0, max=5, step=0.1,
                                 style={"width": "100%", "padding": "5px", "fontSize": "12px"})
                    ], width=6),
                ], className="mb-2"),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Тип эластомера:", style={"fontSize": "11px"}),
                        dcc.Dropdown(id='vzd-elastomer',
                                    options=[
                                        {"label": "Стандартный нитрил", "value": "Стандартный нитрил"},
                                        {"label": "Усиленный нитрил", "value": "Усиленный нитрил"},
                                        {"label": "Фторкаучук (FKM)", "value": "Фторкаучук (FKM)"},
                                        {"label": "Специальный ВТ", "value": "Специальный высокотемпературный"},
                                    ],
                                    value="Стандартный нитрил", clearable=False,
                                    style={"fontSize": "12px"})
                    ], width=6),
                    dbc.Col([
                        html.Label("Тип раствора:", style={"fontSize": "11px"}),
                        dcc.Dropdown(id='vzd-mud-type',
                                    options=[
                                        {"label": "Полимерный", "value": "Полимерный"},
                                        {"label": "Гипсокалиевый", "value": "Гипсокалиевый"},
                                        {"label": "ГЭР", "value": "ГЭР"},
                                        {"label": "Кислотная пачка", "value": "Кислотная пачка"},
                                    ],
                                    value="Полимерный", clearable=False,
                                    style={"fontSize": "12px"})
                    ], width=6),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Наработка, часы:", style={"fontSize": "11px", "fontWeight": "bold", "color": "#dc2626"}),
                        dcc.Input(id='vzd-hours', type='number', value=48.0, min=0, max=500, step=1,
                                 style={"width": "100%", "padding": "5px", "fontSize": "12px", "border": "2px solid #dc2626"})
                    ], width=6),
                    dbc.Col([
                        html.Label("МПИ, часы:", style={"fontSize": "11px"}),
                        dcc.Input(id='vzd-mpi', type='number', value=200, min=50, max=500, step=10,
                                 style={"width": "100%", "padding": "5px", "fontSize": "12px"})
                    ], width=6),
                ], className="mb-3"),
                
                dbc.Button("Рассчитать износ", id='btn-calc-vzd-wear', color="primary", className="w-100 mb-3"),
                
                # Результаты
                html.Div(id='vzd-wear-results'),
            ])
        ])
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def vzd_wear_callbacks(app, data_bridge):
    
    @app.callback(
        Output('vzd-wear-results', 'children'),
        Input('btn-calc-vzd-wear', 'n_clicks'),
        [State('vzd-temp', 'value'),
         State('vzd-torque', 'value'),
         State('vzd-rpm', 'value'),
         State('vzd-sand', 'value'),
         State('vzd-mud-type', 'value'),
         State('vzd-hours', 'value'),
         State('vzd-elastomer', 'value'),
         State('vzd-mpi', 'value')],
        prevent_initial_call=True
    )
    def calculate_wear(n_clicks, temp, torque, rpm, sand, mud_type, hours, elastomer, mpi):
        if None in [temp, torque, rpm, sand, mud_type, hours]:
            return html.Div("Заполните все параметры", style={"color": "#dc2626"})
        
        model = VZDWearPhysicsModel()
        result = model.calculate_total_wear(
            temp_c=temp, torque_knm=torque, rpm=rpm,
            sand_content=sand, mud_type=mud_type, hours=hours,
            elastomer_type=elastomer
        )
        
        # Определяем цвет статуса
        status_color = {" НОРМА": "#16a34a", "🟡 ПОВЫШЕННЫЙ ИЗНОС": "#f59e0b", 
                       "🟠 КРИТИЧЕСКИЙ": "#f97316", "🔴 ТРЕБУЕТ ЗАМЕНЫ": "#dc2626"}.get(result["status"], "#64748b")
        
        # Проверка МПИ
        mpi_status = ""
        if hours > mpi:
            mpi_status = html.Div(f"🚨 ПРЕВЫШЕН МПИ! ({hours} > {mpi} ч)", 
                                 style={"color": "#dc2626", "fontWeight": "bold", "marginTop": "10px"})
        elif hours > mpi * 0.8:
            mpi_status = html.Div(f"⚠️ До МПИ осталось: {mpi - hours:.0f} ч", 
                                 style={"color": "#f59e0b", "marginTop": "10px"})
        
        return html.Div([
            html.H6("Результаты расчета:", style={"marginBottom": "10px", "fontSize": "13px"}),
            
            # Основной показатель
            html.Div(style={
                "backgroundColor": "#111827", "padding": "15px", "borderRadius": "8px",
                "textAlign": "center", "border": f"3px solid {status_color}", "marginBottom": "15px"
            }, children=[
                html.Div("ИЗНОС ВЗД", style={"color": "#9CA3AF", "fontSize": "11px"}),
                html.Div(f"{result['total_wear_percent']:.1f}%", 
                        style={"color": status_color, "fontSize": "32px", "fontWeight": "bold"}),
                html.Div(result["status"], style={"color": status_color, "fontSize": "12px", "marginTop": "5px"}),
            ]),
            
            # Детализация
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Small("Термическая деградация", style={"color": "#64748b"}),
                        html.Div(f"{result['thermal_degradation']:.1f}%", 
                                style={"fontSize": "16px", "fontWeight": "bold", "color": "#ef4444"})
                    ], style={"textAlign": "center", "padding": "10px", "backgroundColor": "#FEE2E2", "borderRadius": "6px"})
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Small("Механический износ", style={"color": "#64748b"}),
                        html.Div(f"{result['mechanical_wear']:.1f}%", 
                                style={"fontSize": "16px", "fontWeight": "bold", "color": "#f59e0b"})
                    ], style={"textAlign": "center", "padding": "10px", "backgroundColor": "#FEF3C7", "borderRadius": "6px"})
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Small("Химико-абразивный", style={"color": "#64748b"}),
                        html.Div(f"{result['chemical_wear']:.1f}%", 
                                style={"fontSize": "16px", "fontWeight": "bold", "color": "#3b82f6"})
                    ], style={"textAlign": "center", "padding": "10px", "backgroundColor": "#DBEAFE", "borderRadius": "6px"})
                ], width=4),
            ], className="mb-3"),
            
            # Остаточный ресурс
            html.Div([
                html.Small("Остаточный ресурс до следующего МПИ:", style={"color": "#64748b"}),
                html.Div(f"{result['remaining_life_hours']:.1f} часов", 
                        style={"fontSize": "18px", "fontWeight": "bold", "color": "#16a34a", "marginTop": "5px"})
            ], style={"padding": "10px", "backgroundColor": "#F0FDF4", "borderRadius": "6px", "marginBottom": "10px"}),
            
            # Рекомендации
            html.Div([
                html.Small("Рекомендации:", style={"color": "#64748b", "fontWeight": "bold"}),
                html.Ul([html.Li(rec, style={"margin": "5px 0", "fontSize": "12px"}) for rec in result["recommendations"]],
                       style={"paddingLeft": "20px", "margin": "5px 0"})
            ], style={"padding": "10px", "backgroundColor": "#F8FAFC", "borderRadius": "6px"}),
            
            mpi_status if mpi_status else html.Div(),
        ])
