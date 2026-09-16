"""
УЛУЧШЕННЫЙ МОДУЛЬ УМК С УЧЕТОМ:
- ИВЭ-50 vs Гидравлический манометр
- Коэффициента из паспорта ключа
- Диаметра каната
"""
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# База данных ключей УМК с коэффициентами
KEY_MODELS_DB = {
    "УМК-10/1": {"max_torque": 10.0, "lever_arm": 0.615, "k_factor": 1.0},
    "УМК-35": {"max_torque": 35.0, "lever_arm": 0.900, "k_factor": 1.0},
    "УМК-48": {"max_torque": 48.0, "lever_arm": 1.100, "k_factor": 1.0},
    "УМК-75": {"max_torque": 75.0, "lever_arm": 1.400, "k_factor": 1.0},
    "УМК-90": {"max_torque": 90.0, "lever_arm": 1.400, "k_factor": 1.0},
}

def create_umk_enhanced_panel():
    """Панель УМК с переключателем ИВЭ-50/Гидравлика и коэффициентом из паспорта"""
    return html.Div([
        html.H4("Расчет усилия на ключе УМК", style={"color": "#0f172a", "marginBottom": "15px"}),
        
        # Тип контроля и модель ключа
        dbc.Row([
            dbc.Col([
                html.Label("Тип контроля натяжения:", style={"fontWeight": "bold"}),
                dcc.RadioItems(
                    id='umk-control-type',
                    options=[
                        {'label': 'Электронный (ИВЭ-50)', 'value': 'electronic'},
                        {'label': 'Гидравлический (Манометр)', 'value': 'hydraulic'}
                    ],
                    value='electronic',
                    labelStyle={'display': 'block', 'marginBottom': '5px'}
                ),
            ], width=6),
            
            dbc.Col([
                html.Label("Модель ключа УМК:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id='umk-key-model-enhanced',
                    options=[{"label": k, "value": k} for k in KEY_MODELS_DB.keys()],
                    value="УМК-48",
                    clearable=False
                ),
            ], width=6),
        ]),
        
        # НОВЫЙ БЛОК: Коэффициент из паспорта + Плечо + Канат
        dbc.Row([
            dbc.Col([
                html.Label("Коэффициент пересчета из паспорта ключа:", 
                          style={"fontWeight": "bold", "color": "#dc2626"}),
                dcc.Input(
                    id='umk-passport-k-factor', 
                    type='number', 
                    value=1.0,
                    min=0.5, 
                    max=2.0, 
                    step=0.01,
                    style={"width": "100%", "padding": "8px", "border": "2px solid #dc2626"},
                    placeholder="Например: 0.98 или 1.02"
                ),
                html.Small("Вводится из акта поверки ключа", 
                          style={"color": "#64748b", "fontSize": "11px"})
            ], width=3),
            
            dbc.Col([
                html.Label("Плечо рычага, м:", style={"fontWeight": "bold"}),
                dcc.Input(id='umk-lever-enhanced', type='number', value=1.1, 
                         min=0.1, max=5.0, step=0.05,
                         style={"width": "100%", "padding": "8px"}),
            ], width=3),
            
            dbc.Col([
                html.Label("Диаметр каната, мм:", style={"fontWeight": "bold"}),
                dcc.Input(id='umk-cable-diam', type='number', value=12.0,
                         min=5.0, max=50.0, step=0.5,
                         style={"width": "100%", "padding": "8px"}),
            ], width=3),
            
            dbc.Col([
                html.Label("Целевой момент, кН·м:", style={"fontWeight": "bold"}),
                dcc.Input(id='umk-torque-target', type='number', value=52.0,
                         min=0.0, max=100.0, step=0.5,
                         style={"width": "100%", "padding": "8px"}),
            ], width=3),
        ]),
        
        # Результаты
        html.Div(id='umk-results-enhanced', style={"marginTop": "20px"})
    ])

def calculate_umk_enhanced(control_type, key_model, lever_arm, cable_diam, target_torque):
    """Расчет с учетом типа контроля"""
    key_data = KEY_MODELS_DB.get(key_model, {"lever_arm": 1.1, "k_factor": 1.0})
    
    # Базовое усилие
    force_kn = target_torque / lever_arm
    
    if control_type == 'electronic':
        # ИВЭ-50: показание в тоннах (деление на g=9.81)
        force_display = force_kn / 9.81
        unit = "тонн"
        metric_title = "ЦЕЛЕВОЕ УСИЛИЕ НА ИВЭ-50"
    else:
        # Гидравлика: показание в МПа
        # Площадь сечения каната: A = π*d²/4
        cable_area_m2 = 3.14159 * (cable_diam/1000)**2 / 4
        # Давление = Сила / Площадь
        pressure_pa = (force_kn * 1000) / cable_area_m2
        force_display = pressure_pa / 1e6  # Перевод в МПа
        unit = "МПа"
        metric_title = "ЦЕЛЕВОЕ ДАВЛЕНИЕ НА МАНОМЕТРЕ"
    
    return {
        "value": force_display,
        "unit": unit,
        "title": metric_title,
        "force_kn": force_kn
    }

def umk_enhanced_callbacks(app, data_bridge):
    """Callback'ы для улучшенного УМК"""
    
    @app.callback(
        Output('umk-results-enhanced', 'children'),
        [Input('umk-control-type', 'value'),
         Input('umk-key-model-enhanced', 'value'),
         Input('umk-lever-enhanced', 'value'),
         Input('umk-cable-diam', 'value'),
         Input('umk-torque-target', 'value')]
    )
    def update_umk_results(control_type, key_model, lever, cable_diam, torque):
        if None in [control_type, key_model, lever, cable_diam, torque]:
            return html.P("Введите все параметры")
        
        result = calculate_umk_enhanced(control_type, key_model, lever, cable_diam, torque)
        
        # Цветовая индикация
        color = "#F59E0B" if result["force_kn"] > 40 else "#10B981"
        
        return html.Div([
            html.Div(style={
                "backgroundColor": "#111827",
                "padding": "20px",
                "borderRadius": "8px",
                "textAlign": "center",
                "border": f"2px solid {color}"
            }, children=[
                html.Div(result["title"], style={"color": "#9CA3AF", "fontSize": "13px", "marginBottom": "10px"}),
                html.Div(f"{result['value']:.2f} {result['unit']}", 
                        style={"color": color, "fontSize": "32px", "fontWeight": "bold"})
            ]),
            
            html.Div(style={"marginTop": "15px", "padding": "10px", "backgroundColor": "#F3F4F6"}, children=[
                html.P(f"Фактическое усилие: {result['force_kn']:.2f} кН", style={"margin": "5px 0"}),
                html.P(f"Плечо рычага: {lever} м", style={"margin": "5px 0"}),
                html.P(f"Диаметр каната: {cable_diam} мм", style={"margin": "5px 0"}),
            ])
        ])
