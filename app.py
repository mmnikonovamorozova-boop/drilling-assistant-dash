"""
ГЛАВНЫЙ ФАЙЛ ПРИЛОЖЕНИЯ
Drilling Assistant - Industrial Dashboard
"""
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from modules.bha_assembly import bha_assembly_layout, bha_assembly_callbacks
from utils.data_bridge import DataBridge

# Инициализация
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server # Для деплоя

data_bridge = DataBridge()

# --- МАКЕТ ПРИЛОЖЕНИЯ ---
app.layout = html.Div([
    
    # 1. ВЕРХНЯЯ ШАПКА (HEADER)
    html.Div(className="app-header", children=[
        html.Div([
            html.H1("СИСТЕМА КОНТРОЛЯ СБОРКИ КНБК"),
            html.Div(className="meta-info", children="СТО ИНТИ S.QS.7 | Модуль: Виртуальный ротор и Входной контроль")
        ]),
        html.Div(className="meta-info", children=[
            html.Span("Инженер: ", style={"color": "#fff"}),
            html.Span(id='header-engineer', children="Иванов И.И."),
            html.Span(" | Скважина: ", style={"color": "#fff", "marginLeft": "15px"}),
            html.Span(id='header-well', children="Приобское №101"),
        ])
    ]),

    # 2. ОСНОВНОЙ КОНТЕЙНЕР
    dbc.Container(fluid=True, className="mt-4", children=[
        dbc.Row([
            
            # ЛЕВАЯ/ЦЕНТРАЛЬНАЯ ЧАСТЬ (ВКЛАДКИ И ТАБЛИЦЫ)
            dbc.Col(width=9, children=[
                dcc.Tabs(
                    id='main-tabs',
                    value='tab-input',
                    className='custom-tabs',
                    children=[
                        dcc.Tab(label='1. Входной контроль элементов', value='tab-input'),
                        dcc.Tab(label='2. Визуальная схема и стыки', value='tab-visual'),
                        dcc.Tab(label='3. Расчет УМК и натяжения', value='tab-umk'),
                    ]
                ),
                # Сюда будет подгружаться контент вкладок
                html.Div(id='tabs-content', className="mt-3")
            ]),

            # ПРАВАЯ ПАНЕЛЬ (КОНТРОЛЬ ВЗД - ВСЕГДА НА ВИДУ)
            dbc.Col(width=3, children=[
                html.Div(className="right-panel", children=[
                    html.Div(className="panel-title", children="КОНТРОЛЬ ИЗНОСА ВЗД"),
                    html.Div(id='vzd-panel-content') # Контент панели ВЗД
                ])
            ])
        ])
    ]),

    # 3. НИЖНЯЯ ПАНЕЛЬ ДЕЙСТВИЙ (ACTION BAR)
    html.Div(className="bottom-action-bar", children=[
        html.Div(className="action-metrics", children=[
            html.Div([
                html.Span("РИСК РЕЙСА: ", style={"color": "#94a3b8"}),
                html.Span(id='metric-risk', children="23%", style={"color": "#16a34a", "fontWeight": "bold"})
            ]),
            html.Div([
                html.Span("СТАТУС ВЗД: ", style={"color": "#94a3b8"}),
                html.Span(id='metric-vzd-status', children="ОТБРАКОВАН", style={"color": "#dc2626", "fontWeight": "bold"})
            ]),
            html.Div([
                html.Span("УСИЛИЕ НАТЯЖЕНИЯ: ", style={"color": "#94a3b8"}),
                html.Span(id='metric-tension', children="6.38 т", style={"color": "#fff", "fontWeight": "bold"})
            ]),
        ]),
        html.Div(children=[
            html.Button("Сформировать акт СМК", className="action-btn btn-primary", style={"marginRight": "10px"}),
            html.Button("Запросить замену ВЗД", className="action-btn btn-danger", style={"marginRight": "10px"}),
            html.Button("Ручной ввод данных", className="action-btn btn-outline"),
        ])
    ])
])

# Регистрируем callback'и модуля
bha_assembly_callbacks(app, data_bridge)

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)
