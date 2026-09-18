"""
МОДУЛЬ ПРОГНОЗА ТРАЕКТОРИИ И УПРАВЛЕНИЯ ИНТЕНСИВНОСТЬЮ (DLS)
Предиктивное моделирование по методу минимальной кривизны (MCM),
расчет DDI, аудит коммерческих рисков и адаптивное самообучение коэффициентов КНБК.
"""
import math
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.compliance_engine import get_compliance_engine
from utils.data_bridge import DataBridge

compliance = get_compliance_engine()
data_bridge = DataBridge()

def calculate_mcm(md: List[float], inc: List[float], azi: List[float]) -> pd.DataFrame:
    n = len(md)
    tvd, north, east, dls = [0.0]*n, [0.0]*n, [0.0]*n, [0.0]*n
    tvd[0], north[0], east[0] = md[0], 0.0, 0.0
    for i in range(1, n):
        dl_md = md[i] - md[i-1]
        if dl_md <= 0:
            tvd[i], north[i], east[i] = tvd[i-1], north[i-1], east[i-1]
            continue
        inc1, inc2 = math.radians(inc[i-1]), math.radians(inc[i])
        azi1, azi2 = math.radians(azi[i-1]), math.radians(azi[i])
        cos_alpha = math.cos(inc1)*math.cos(inc2) + math.sin(inc1)*math.sin(inc2)*math.cos(azi2 - azi1)
        cos_alpha = max(-1.0, min(1.0, cos_alpha))
        alpha = math.acos(cos_alpha)
        rf = (2.0 / alpha) * math.tan(alpha / 2.0) if alpha > 0.001 else 1.0
        tvd[i] = tvd[i-1] + (dl_md / 2.0) * (math.cos(inc1) + math.cos(inc2)) * rf
        north[i] = north[i-1] + (dl_md / 2.0) * (math.sin(inc1)*math.cos(azi1) + math.sin(inc2)*math.cos(azi2)) * rf
        east[i] = east[i-1] + (dl_md / 2.0) * (math.sin(inc1)*math.sin(azi1) + math.sin(inc2)*math.sin(azi2)) * rf
        dls[i] = math.degrees(alpha) / (dl_md / 10.0) if dl_md > 0 else 0.0
    return pd.DataFrame({"MD": md, "INC": inc, "AZI": azi, "TVD": tvd, "NORTH": north, "EAST": east, "DLS": dls})

def predict_next_point(current_md, current_inc, current_azi, k_slide, k_rotary, slide_pct, tool_face, formation_anisotropy, rheology_mod, length):
    slide_frac = slide_pct / 100.0
    build_slide = 0.45 * k_slide * math.cos(math.radians(tool_face)) * rheology_mod
    build_rotary = 0.02 * k_rotary + (formation_anisotropy * 0.5)
    d_inc_per_10m = (build_slide * slide_frac) + (build_rotary * (1.0 - slide_frac))
    turn_slide = 0.45 * k_slide * math.sin(math.radians(tool_face)) * rheology_mod
    turn_rotary = -0.015 * (1.0 - formation_anisotropy)
    d_azi_per_10m = (turn_slide * slide_frac) + (turn_rotary * (1.0 - slide_frac))
    next_md = current_md + length
    next_inc = max(0.0, min(90.0, current_inc + (d_inc_per_10m / 10.0) * length))
    next_azi = (current_azi + (d_azi_per_10m / 10.0) * length) % 360.0
    forecast_dls = abs(d_inc_per_10m)
    return next_md, next_inc, next_azi, forecast_dls

def create_trajectory_layout():
    return html.Div([
        html.Div([
            html.H2("Предиктивное моделирование траектории и DLS", style={"color": "white", "margin": "0"}),
            html.P("Прогноз пространственного положения, аудит коммерческих рисков и адаптация КНБК", style={"color": "#BFDBFE", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], className="module-header"),
        
        dbc.Row([
            dbc.Col([html.Label("Заказчик (для лимитов ТК):", style={"fontWeight": "bold", "fontSize": "13px"}), dcc.Dropdown(id='traj-client', options=[{"label": "Роснефть", "value": "Роснефть"}, {"label": "Газпром нефть", "value": "Газпром нефть"}, {"label": "ЛУКОЙЛ", "value": "ЛУКОЙЛ"}, {"label": "Татнефть", "value": "Татнефть"}, {"label": "Прочие", "value": "Прочие"}], value="Роснефть", clearable=False)], width=3),
            dbc.Col([html.Label("Текущая глубина MD, м:", style={"fontWeight": "bold", "fontSize": "13px"}), dcc.Input(id='traj-curr-md', type='number', value=2500.0, style={"width": "100%", "padding": "8px"})], width=3),
            dbc.Col([html.Label("Текущий зенит (INC), °:", style={"fontWeight": "bold", "fontSize": "13px"}), dcc.Input(id='traj-curr-inc', type='number', value=45.0, style={"width": "100%", "padding": "8px"})], width=3),
            dbc.Col([html.Label("Текущий азимут (AZI), °:", style={"fontWeight": "bold", "fontSize": "13px"}), dcc.Input(id='traj-curr-azi', type='number', value=120.0, style={"width": "100%", "padding": "8px"})], width=3),
        ], className="mb-4"),

        dcc.Tabs(id='traj-tabs', value='tab-forecast', className='custom-tabs', children=[
            dcc.Tab(label='Прогноз и График', value='tab-forecast'),
            dcc.Tab(label='Коммерческие риски (DLS)', value='tab-risks'),
            dcc.Tab(label='Самообучение КНБК', value='tab-learning'),
        ]),
        
        # ВСЕ ВКЛАДКИ СОЗДАНЫ СРАЗУ
        html.Div(id='traj-forecast-tab', children=[
            html.H4("Параметры прогнозного интервала", style={"color": "#1E40AF", "marginBottom": "15px", "marginTop": "20px"}),
            dbc.Row([
                dbc.Col([html.Label("Длина интервала, м:", style={"fontWeight": "bold"}), dcc.Input(id='traj-length', type='number', value=30.0, min=10, max=100, style={"width": "100%", "padding": "8px"})], width=3),
                dbc.Col([html.Label("Доля слайда, %:", style={"fontWeight": "bold"}), dcc.Input(id='traj-slide-pct', type='number', value=40.0, min=0, max=100, style={"width": "100%", "padding": "8px"})], width=3),
                dbc.Col([html.Label("Tool Face, °:", style={"fontWeight": "bold"}), dcc.Input(id='traj-tf', type='number', value=45.0, min=0, max=360, style={"width": "100%", "padding": "8px"})], width=3),
                dbc.Col([html.Label("Анизотропия пласта:", style={"fontWeight": "bold"}), dcc.Input(id='traj-aniso', type='number', value=0.05, min=0, max=0.2, step=0.01, style={"width": "100%", "padding": "8px"})], width=3),
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([html.Div(className="metric-card", children=[html.Div(className="metric-label", children="ПРОГНОЗ MD"), html.Div(id='traj-res-md', className="metric-value", children="0.0 м")])], width=3),
                dbc.Col([html.Div(className="metric-card", children=[html.Div(className="metric-label", children="ПРОГНОЗ INC"), html.Div(id='traj-res-inc', className="metric-value", children="0.0 °")])], width=3),
                dbc.Col([html.Div(className="metric-card", children=[html.Div(className="metric-label", children="ПРОГНОЗ AZI"), html.Div(id='traj-res-azi', className="metric-value", children="0.0 °")])], width=3),
                dbc.Col([html.Div(className="metric-card", children=[html.Div(className="metric-label", children="ПРОГНОЗ DLS"), html.Div(id='traj-res-dls', className="metric-value", children="0.0 °/10м")])], width=3),
            ], className="mb-4"),
            html.H4("Профиль траектории (План vs Прогноз)", style={"color": "#1E40AF", "marginBottom": "10px"}),
            dcc.Graph(id='traj-profile-chart', style={"height": "500px"}),
        ], style={"marginTop": "20px"}),
        
        html.Div(id='traj-risks-tab', children=[
            html.H4("Аудит коммерческих рисков по DLS", style={"color": "#1E40AF", "marginBottom": "15px", "marginTop": "20px"}),
            dbc.Row([
                dbc.Col([html.Label("Макс. лимит DLS по ТК, °/10м:", style={"fontWeight": "bold"}), dcc.Input(id='traj-dls-max', type='number', value=3.0, step=0.1, style={"width": "100%", "padding": "8px"})], width=4),
                dbc.Col([html.Label("Мин. набор DLS по ТК, °/10м:", style={"fontWeight": "bold"}), dcc.Input(id='traj-dls-min', type='number', value=0.5, step=0.1, style={"width": "100%", "padding": "8px"})], width=4),
                dbc.Col([html.Label("Последние 2 фактических замера DLS:", style={"fontWeight": "bold"}), dbc.InputGroup([dbc.Input(id='traj-dls-hist-1', type='number', value=2.8, step=0.1), dbc.Input(id='traj-dls-hist-2', type='number', value=2.9, step=0.1)])], width=4),
            ], className="mb-4"),
            html.Div(id='traj-penalty-alert', className="mb-4"),
            html.H5("Рекомендация по режиму бурения на интервал:", style={"color": "#1E40AF", "marginBottom": "10px"}),
            dbc.Row([
                dbc.Col([html.Div(className="metric-card", children=[html.Div(className="metric-label", children="РЕКОМЕНДУЕМЫЙ СЛАЙД"), html.Div(id='traj-rec-slide', className="metric-value", children="0.0 м")])], width=6),
                dbc.Col([html.Div(className="metric-card", children=[html.Div(className="metric-label", children="РЕКОМЕНДУЕМЫЙ РОТОР"), html.Div(id='traj-rec-rotary', className="metric-value", children="0.0 м")])], width=6),
            ]),
        ], style={"display": "none", "marginTop": "20px"}),
        
        html.Div(id='traj-learning-tab', children=[
            html.H4("Адаптивное самообучение коэффициентов КНБК", style={"color": "#1E40AF", "marginBottom": "15px", "marginTop": "20px"}),
            html.P("Введите фактические данные по отработанному интервалу для корректировки модели увода.", style={"color": "#64748B", "marginBottom": "15px"}),
            dbc.Row([
                dbc.Col([html.Label("Факт. длина интервала, м:", style={"fontWeight": "bold"}), dcc.Input(id='learn-length', type='number', value=30.0, style={"width": "100%", "padding": "8px"})], width=4),
                dbc.Col([html.Label("Факт. набранный угол (INC), °:", style={"fontWeight": "bold"}), dcc.Input(id='learn-inc', type='number', value=1.2, step=0.1, style={"width": "100%", "padding": "8px"})], width=4),
                dbc.Col([html.Label("Факт. доля слайда, %:", style={"fontWeight": "bold"}), dcc.Input(id='learn-slide-pct', type='number', value=40.0, style={"width": "100%", "padding": "8px"})], width=4),
            ], className="mb-4"),
            dbc.Button("🚀 Рассчитать и применить новые коэффициенты", id='btn-learn-k', color="primary", className="w-100 mb-3"),
            html.Div(id='learn-results', className="mb-4"),
            html.H5("Журнал рекомендаций рейса", style={"color": "#1E40AF", "marginBottom": "10px"}),
            html.Div(id='traj-journal-table'),
            dbc.Button("Очистить журнал", id='btn-clear-journal', color="danger", size="sm", className="mt-2"),
        ], style={"display": "none", "marginTop": "20px"}),
        
        dcc.Store(id='traj-journal-store', data=[]),
    ])

def trajectory_forecast_callbacks(app, data_bridge):
    
    @app.callback(
        [Output('traj-forecast-tab', 'style'), Output('traj-risks-tab', 'style'), Output('traj-learning-tab', 'style')],
        Input('traj-tabs', 'value'),
        prevent_initial_call=True
    )
    def render_traj_tab(tab):
        hidden = {"display": "none", "marginTop": "20px"}
        visible = {"display": "block", "marginTop": "20px"}
        if tab == 'tab-forecast': return visible, hidden, hidden
        if tab == 'tab-risks': return hidden, visible, hidden
        if tab == 'tab-learning': return hidden, hidden, visible
        return hidden, hidden, hidden

    @app.callback(
        [Output('traj-dls-max', 'value'), Output('traj-dls-min', 'value')],
        Input('traj-client', 'value'),
        prevent_initial_call=True
    )
    def update_limits_from_compliance(client):
        dls_max, _, _ = compliance.get_limit(client, 'dls_limit', 'max_dls', 3.0)
        dls_min, _, _ = compliance.get_limit(client, 'dls_limit', 'min_dls', 0.5)
        return float(dls_max), float(dls_min)

    @app.callback(
        [Output('traj-res-md', 'children'), Output('traj-res-inc', 'children'), 
         Output('traj-res-azi', 'children'), Output('traj-res-dls', 'children'),
         Output('traj-profile-chart', 'figure')],
        [Input('traj-curr-md', 'value'), Input('traj-curr-inc', 'value'), Input('traj-curr-azi', 'value'),
         Input('traj-length', 'value'), Input('traj-slide-pct', 'value'), Input('traj-tf', 'value'),
         Input('traj-aniso', 'value')],
        prevent_initial_call=True
    )
    def calculate_forecast(md, inc, azi, length, slide_pct, tf, aniso):
        if None in [md, inc, azi, length, slide_pct, tf, aniso]:
            return "0.0", "0.0", "0.0", "0.0", go.Figure()
        k_slide = data_bridge.get_data('k_slide', 0.45)
        k_rotary = data_bridge.get_data('k_rotary', 0.02)
        rheo_mod = 1.0
        next_md, next_inc, next_azi, forecast_dls = predict_next_point(md, inc, azi, k_slide, k_rotary, slide_pct, tf, aniso, rheo_mod, length)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[md, next_md], y=[inc, inc + (forecast_dls/10)*length], name="Прогноз", line=dict(color="#3B82F6", width=3, dash="dot")))
        fig.add_trace(go.Scatter(x=[md, next_md], y=[3.0, 3.0], name="Лимит DLS", line=dict(color="#EF4444", width=2)))
        fig.update_layout(title="Прогноз изменения зенитного угла", xaxis_title="Глубина MD, м", yaxis_title="Зенитный угол INC, °", template="plotly_white", height=500)
        return (f"{next_md:.1f} м", f"{next_inc:.2f} °", f"{next_azi:.2f} °", f"{forecast_dls:.2f} °/10м", fig)

    @app.callback(
        [Output('traj-penalty-alert', 'children'), Output('traj-rec-slide', 'children'), Output('traj-rec-rotary', 'children')],
        [Input('traj-dls-max', 'value'), Input('traj-dls-min', 'value'),
         Input('traj-dls-hist-1', 'value'), Input('traj-dls-hist-2', 'value'),
         Input('traj-res-dls', 'children')],
        prevent_initial_call=True
    )
    def check_penalties(dls_max, dls_min, hist1, hist2, forecast_dls_str):
        if None in [dls_max, dls_min, hist1, hist2] or not forecast_dls_str:
            return html.Div(), "0.0 м", "0.0 м"
        forecast_dls = float(forecast_dls_str.split()[0])
        history = [hist1, hist2, forecast_dls]
        violations = 0
        for d in history:
            if d > dls_max or d < dls_min:
                violations += 1
        if violations >= 3:
            alert = dbc.Alert("🚨 КРИТИЧЕСКИЙ РИСК ШТРАФА: 3 последовательных нарушения лимита DLS! Срочно измените Tool Face или долю слайда.", color="danger")
        elif violations > 0:
            alert = dbc.Alert(f"⚠️ ВНИМАНИЕ: Серия нарушений ({violations} из 3). Требуется коррекция траектории.", color="warning")
        else:
            alert = dbc.Alert("✅ Профиль в коридоре. Коммерческие риски отсутствуют.", color="success")
        rec_slide = 30.0 if forecast_dls < dls_min else 10.0
        rec_rotary = 30.0 - rec_slide
        return alert, f"{rec_slide:.1f} м", f"{rec_rotary:.1f} м"

    @app.callback(
        Output('learn-results', 'children'),
        Input('btn-learn-k', 'n_clicks'),
        [State('traj-curr-md', 'value'), State('traj-curr-inc', 'value'), State('traj-curr-azi', 'value'),
         State('learn-length', 'value'), State('learn-inc', 'value'), State('learn-slide-pct', 'value')],
        prevent_initial_call=True
    )
    def adapt_k_factors(n_clicks, curr_md, curr_inc, curr_azi, length, actual_inc, slide_pct):
        if not n_clicks or None in [curr_md, curr_inc, length, actual_inc, slide_pct]:
            return html.Div()
        k_slide = data_bridge.get_data('k_slide', 0.45)
        k_rotary = data_bridge.get_data('k_rotary', 0.02)
        tf = 45.0
        aniso = 0.05
        _, pred_inc, _, _ = predict_next_point(curr_md, curr_inc, 0, k_slide, k_rotary, slide_pct, tf, aniso, 1.0, length)
        pred_inc_change = pred_inc - curr_inc
        error = actual_inc - pred_inc_change
        lr = 0.1
        slide_frac = slide_pct / 100.0
        new_k_slide = max(0.1, min(1.5, k_slide + (error * lr * slide_frac)))
        new_k_rotary = max(0.001, min(0.2, k_rotary + (error * lr * (1.0 - slide_frac) * 0.1)))
        data_bridge.set_data('k_slide', new_k_slide)
        data_bridge.set_data('k_rotary', new_k_rotary)
        return dbc.Alert([
            html.Strong("✅ Коэффициенты адаптированы!"),
            html.Br(),
            f"K_slide: {k_slide:.3f} → {new_k_slide:.3f}", html.Br(),
            f"K_rotary: {k_rotary:.3f} → {new_k_rotary:.3f}", html.Br(),
            f"Ошибка прогноза: {abs(error):.2f}°"
        ], color="success")
