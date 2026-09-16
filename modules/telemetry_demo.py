"""
ДЕМО-МОДУЛЬ ТЕЛЕМЕТРИИ (WITSML SIMULATOR)
Генерация реалистичных данных бурения в реальном времени
для демонстрации возможностей приложения руководству
"""
import random
import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class WITSMLSimulator:
    """Генератор реалистичных телеметрических данных"""
    
    def __init__(self):
        self.md = 2500.0  # Начальная глубина
        self.time = datetime.now()
        self.base_rop = 35.0
        self.base_wob = 15.0
        self.base_torque = 8.5
        self.base_spp = 210.0
        self.flow_rate = 28.0
        self.vibration = 1.2
        self.incident_active = None
        self.incident_timer = 0
        
    def generate_next_point(self, time_delta_sec: int = 10) -> Dict:
        """Генерирует следующую точку телеметрии"""
        self.time += timedelta(seconds=time_delta_sec)
        self.md += (self.base_rop / 3600) * time_delta_sec
        
        # Добавляем случайный шум (как в реальной телеметрии)
        noise = lambda x, pct=0.05: x * (1 + random.uniform(-pct, pct))
        
        point = {
            "time": self.time.isoformat(),
            "md": round(self.md, 2),
            "tvd": round(self.md * 0.95, 2),  # Упрощенно
            "wob": round(noise(self.base_wob), 2),
            "rop": round(noise(self.base_rop), 2),
            "torque": round(noise(self.base_torque), 2),
            "spp": round(noise(self.base_spp), 2),
            "flow_in": round(noise(self.flow_rate), 2),
            "flow_out": round(noise(self.flow_rate), 2),
            "vibration_axial": round(noise(self.vibration, 0.1), 3),
            "vibration_radial": round(noise(self.vibration * 0.8, 0.1), 3),
            "rpm": round(noise(120), 1),
            "hook_load": round(noise(180), 1),
        }
        
        # Симуляция инцидентов
        self._simulate_incidents(point)
        
        return point
    
    def _simulate_incidents(self, point: Dict):
        """Добавляет аномалии в данные (прихват, потеря циркуляции и т.д.)"""
        # Случайный запуск инцидента (5% шанс)
        if self.incident_active is None and random.random() < 0.05:
            incident_type = random.choice(["stick_slip", "vibration", "losses", "packoff"])
            self.incident_active = incident_type
            self.incident_timer = random.randint(30, 90)  # Длительность 30-90 секунд
        
        if self.incident_active:
            if self.incident_active == "stick_slip":
                point["torque"] *= random.uniform(1.5, 2.5)
                point["rop"] *= random.uniform(0.2, 0.5)
                point["wob"] *= random.uniform(0.8, 1.2)
            elif self.incident_active == "vibration":
                point["vibration_axial"] *= random.uniform(3, 6)
                point["vibration_radial"] *= random.uniform(3, 6)
            elif self.incident_active == "losses":
                point["flow_out"] *= random.uniform(0.6, 0.8)
                point["spp"] *= random.uniform(0.85, 0.95)
            elif self.incident_active == "packoff":
                point["hook_load"] *= random.uniform(1.2, 1.5)
                point["torque"] *= random.uniform(1.3, 1.8)
            
            self.incident_timer -= 1
            if self.incident_timer <= 0:
                self.incident_active = None


def create_telemetry_demo_layout():
    """Макет демо-модуля телеметрии"""
    return html.Div([
        html.Div([
            html.H2("Демонстрация работы с телеметрией (WITSML)", style={"color": "white", "margin": "0"}),
            html.P("Симуляция реального времени | Интеграция с RTOC", 
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "20px", "borderRadius": "8px", "marginBottom": "20px"}),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Управление симуляцией", className="mb-3"),
                        dbc.Button("▶️ Запустить симуляцию", id='btn-start-sim', color="success", className="w-100 mb-2"),
                        dbc.Button("⏸️ Пауза", id='btn-pause-sim', color="warning", className="w-100 mb-2"),
                        dbc.Button("🔄 Сбросить", id='btn-reset-sim', color="danger", className="w-100"),
                        html.Hr(),
                        html.H6("Текущий статус:", className="mb-2"),
                        html.Div(id='sim-status-indicator', children=html.Span("⏸️ Остановлено", style={"color": "#64748B", "fontWeight": "bold"})),
                    ])
                ])
            ], width=3),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Параметры бурения (Real-Time)", className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.Div(className="metric-card", children=[
                                    html.Div(className="metric-label", children="WOB"),
                                    html.Div(id='sim-wob-val', className="metric-value", children="0.0 т")
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div(className="metric-card", children=[
                                    html.Div(className="metric-label", children="ROP"),
                                    html.Div(id='sim-rop-val', className="metric-value", children="0.0 м/ч")
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div(className="metric-card", children=[
                                    html.Div(className="metric-label", children="SPP"),
                                    html.Div(id='sim-spp-val', className="metric-value", children="0.0 атм")
                                ])
                            ], width=4),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                html.Div(className="metric-card", children=[
                                    html.Div(className="metric-label", children="TORQUE"),
                                    html.Div(id='sim-torque-val', className="metric-value", children="0.0 кН·м")
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div(className="metric-card", children=[
                                    html.Div(className="metric-label", children="FLOW IN"),
                                    html.Div(id='sim-flow-val', className="metric-value", children="0.0 л/с")
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div(className="metric-card", children=[
                                    html.Div(className="metric-label", children="ВИБРАЦИЯ"),
                                    html.Div(id='sim-vib-val', className="metric-value", children="0.0 g")
                                ])
                            ], width=4),
                        ]),
                    ])
                ])
            ], width=9),
        ], className="mb-4"),
        
        # Графики в реальном времени
        html.Div([
            dcc.Graph(id='sim-wob-rop-chart', style={"height": "350px"}),
            dcc.Graph(id='sim-torque-spp-chart', style={"height": "350px"}),
            dcc.Graph(id='sim-vibration-chart', style={"height": "300px"}),
        ]),
        
        # Алерты
        html.Div(id='sim-alerts-panel', className="mt-3"),
        
        # Интервал обновления
        dcc.Interval(id='sim-interval', interval=1000, disabled=True),  # 1 секунда
        dcc.Store(id='sim-data-store', data=[]),
    ])


def telemetry_demo_callbacks(app, data_bridge):
    """Callback'и для демо-модуля"""
    
    simulator = WITSMLSimulator()
    
    @app.callback(
        Output('sim-interval', 'disabled'),
        Output('sim-status-indicator', 'children'),
        Input('btn-start-sim', 'n_clicks'),
        Input('btn-pause-sim', 'n_clicks'),
        Input('btn-reset-sim', 'n_clicks'),
        prevent_initial_call=True
    )
    def control_simulation(start_clicks, pause_clicks, reset_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return True, html.Span("️ Остановлено", style={"color": "#64748B"})
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'btn-start-sim':
            return False, html.Span("▶️ Работает (Real-Time)", style={"color": "#10B981", "fontWeight": "bold"})
        elif button_id == 'btn-pause-sim':
            return True, html.Span("⏸️ Пауза", style={"color": "#F59E0B", "fontWeight": "bold"})
        elif button_id == 'btn-reset-sim':
            simulator.__init__()  # Сброс
            return True, html.Span("🔄 Сброшено", style={"color": "#64748B"})
        
        return True, html.Span("️ Остановлено")
    
    @app.callback(
        [Output('sim-wob-val', 'children'),
         Output('sim-rop-val', 'children'),
         Output('sim-spp-val', 'children'),
         Output('sim-torque-val', 'children'),
         Output('sim-flow-val', 'children'),
         Output('sim-vib-val', 'children'),
         Output('sim-wob-rop-chart', 'figure'),
         Output('sim-torque-spp-chart', 'figure'),
         Output('sim-vibration-chart', 'figure'),
         Output('sim-alerts-panel', 'children'),
         Output('sim-data-store', 'data')],
        Input('sim-interval', 'n_intervals'),
        State('sim-data-store', 'data')
    )
    def update_telemetry(n_intervals, stored_data):
        # Генерация новой точки
        point = simulator.generate_next_point()
        
        # Добавляем в историю
        if stored_data is None:
            stored_data = []
        stored_data.append(point)
        if len(stored_data) > 100:  # Храним последние 100 точек
            stored_data = stored_data[-100:]
        
        # Обновление метрик
        wob_val = f"{point['wob']} т"
        rop_val = f"{point['rop']} м/ч"
        spp_val = f"{point['spp']} атм"
        torque_val = f"{point['torque']} кН·м"
        flow_val = f"{point['flow_in']} л/с"
        vib_val = f"{point['vibration_axial']} g"
        
        # Графики
        df = pd.DataFrame(stored_data)
        times = [datetime.fromisoformat(t).strftime("%H:%M:%S") for t in df['time']]
        
        # График WOB/ROP
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=times, y=df['wob'], name='WOB', line=dict(color='#3B82F6', width=2)))
        fig1.add_trace(go.Scatter(x=times, y=df['rop'], name='ROP', line=dict(color='#10B981', width=2), yaxis='y2'))
        fig1.update_layout(title="WOB и ROP", xaxis_title="Время", yaxis_title="WOB (т)", 
                          yaxis2=dict(title="ROP (м/ч)", overlaying='y', side='right'),
                          template='plotly_white', height=350, margin=dict(l=40, r=40, t=40, b=40))
        
        # График Torque/SPP
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=times, y=df['torque'], name='Torque', line=dict(color='#F59E0B', width=2)))
        fig2.add_trace(go.Scatter(x=times, y=df['spp'], name='SPP', line=dict(color='#EF4444', width=2), yaxis='y2'))
        fig2.update_layout(title="Крутящий момент и давление", xaxis_title="Время", yaxis_title="Torque (кН·м)",
                          yaxis2=dict(title="SPP (атм)", overlaying='y', side='right'),
                          template='plotly_white', height=350, margin=dict(l=40, r=40, t=40, b=40))
        
        # График вибраций
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=times, y=df['vibration_axial'], name='Axial', line=dict(color='#8B5CF6', width=2)))
        fig3.add_trace(go.Scatter(x=times, y=df['vibration_radial'], name='Radial', line=dict(color='#EC4899', width=2)))
        fig3.add_hline(y=5.0, line_dash="dash", line_color="#EF4444", annotation_text="Критический уровень")
        fig3.update_layout(title="Вибрации", xaxis_title="Время", yaxis_title="g",
                          template='plotly_white', height=300, margin=dict(l=40, r=40, t=40, b=40))
        
        # Алерты
        alerts = []
        if point['vibration_axial'] > 5.0:
            alerts.append(dbc.Alert(" КРИТИЧЕСКАЯ ВИБРАЦИЯ! Рекомендуется снизить WOB", color="danger", duration=3000))
        if simulator.incident_active:
            incident_name = {
                "stick_slip": "Stick-Slip",
                "vibration": "Повышенная вибрация",
                "losses": "Потеря циркуляции",
                "packoff": "Прихват/Затяжка"
            }.get(simulator.incident_active, simulator.incident_active)
            alerts.append(dbc.Alert(f"⚠️ Обнаружено осложнение: {incident_name}", color="warning", duration=5000))
        
        alerts_panel = html.Div(alerts) if alerts else html.Div()
        
        return (wob_val, rop_val, spp_val, torque_val, flow_val, vib_val,
                fig1, fig2, fig3, alerts_panel, stored_data)
