"""
МОДУЛЬ КОНТРОЛЯ ИЗНОСА ВЗД
Простая заглушка для демонстрации
"""
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

def create_vzd_wear_panel():
    """Панель контроля износа ВЗД"""
    return html.Div([
        html.H5("Контроль износа ВЗД", style={"color": "#0f172a", "marginBottom": "15px"}),
        
        dbc.Card([
            dbc.CardBody([
                html.P("Модуль контроля износа ВЗД находится в разработке.", 
                      style={"color": "#64748b", "marginBottom": "10px"}),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Текущая наработка, часы:", style={"fontWeight": "bold", "fontSize": "12px"}),
                        dcc.Input(type='number', value=48.0, style={"width": "100%", "padding": "5px"})
                    ], width=6),
                    dbc.Col([
                        html.Label("Остаточный ресурс, часы:", style={"fontWeight": "bold", "fontSize": "12px"}),
                        html.Div("152.0 ч", style={"fontSize": "18px", "fontWeight": "bold", "color": "#16a34a", "marginTop": "5px"})
                    ], width=6),
                ], className="mb-3"),
                
                html.Hr(),
                
                html.P("Статус: 🟢 НОРМА", style={"fontSize": "14px", "fontWeight": "bold", "color": "#16a34a", "margin": "10px 0"}),
            ])
        ])
    ])

def vzd_wear_callbacks(app, data_bridge):
    """Callback'и для модуля ВЗД (заглушка)"""
    pass
