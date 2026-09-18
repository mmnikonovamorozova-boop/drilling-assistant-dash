"""
ГЛАВНЫЙ ФАЙЛ ПРИЛОЖЕНИЯ
Drilling Assistant - Industrial Dashboard 2024
Архитектура с разделением ролей: Полевой режим / Офисный режим
"""
import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

from utils.data_bridge import DataBridge
from components.sidebar import create_sidebar

# Импорт всех модулей
from modules.auth import auth_layout, auth_callbacks
from modules.role_selection import create_role_selection_layout, role_selection_callbacks
from modules.bha_assembly import bha_assembly_layout, bha_assembly_callbacks
from modules.mud_control import create_mud_control_layout, mud_control_callbacks
from modules.trajectory_forecast import create_trajectory_layout, trajectory_forecast_callbacks
from modules.compliance_checklist import create_compliance_layout, compliance_checklist_callbacks
from modules.knowledge_base_admin import create_kb_admin_layout, kb_admin_callbacks
from modules.telemetry_demo import create_telemetry_demo_layout, telemetry_demo_callbacks
from modules.resistivity_sub_control import create_resistivity_control_layout, resistivity_control_callbacks
from modules.bha_telemetry_system import create_telemetry_system_layout, telemetry_system_callbacks
from modules.stress_testing import create_stress_test_layout, stress_test_callbacks
from modules.background_monitor import monitor

# 1. Инициализация приложения
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ],
    suppress_callback_exceptions=True,
    assets_folder='assets'
)
server = app.server

# Глобальный шлюз данных
data_bridge = DataBridge()

# Запуск фонового мониторинга
monitor.start()

# 2. МАКЕТ ПРИЛОЖЕНИЯ
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='session-data', storage_type='session'),

    html.Div(id='app-header', className="app-header", children=[
        html.Div([
            html.H1("Drilling Assistant", style={"fontSize": "24px", "margin": "0", "fontWeight": "700"}),
            html.Div("Промышленный стандарт контроля буровых работ", style={"fontSize": "13px", "color": "#BFDBFE", "marginTop": "4px"})
        ]),
        html.Div([
            html.Span("Пользователь: ", style={"color": "#BFDBFE"}),
            html.Span(id='header-user', children="Гость", style={"fontWeight": "600", "color": "white"}),
        ], style={"backgroundColor": "rgba(255,255,255,0.1)", "padding": "8px 16px", "borderRadius": "8px"})
    ]),

    dbc.Container(fluid=True, className="mt-4", children=[
        dbc.Row([
            dbc.Col(create_sidebar(), width=2, className="sidebar", style={"minHeight": "100vh"}),
            dbc.Col(width=10, children=[
                html.Div(id='page-content')
            ])
        ])
    ]),

    html.Div(id='bottom-action-bar', className="bottom-action-bar", children=[
        html.Div(className="action-metrics", children=[
            html.Div([html.Span("СТАТУС СИСТЕМЫ: ", style={"color": "#94a3b8"}), html.Span("АКТИВНА", style={"color": "#10B981", "fontWeight": "bold"})]),
        ]),
        html.Div(children=[
            html.Button("Сформировать отчет", className="action-btn btn-primary", style={"marginRight": "10px"}),
            html.Button("Справка", className="action-btn btn-outline"),
        ])
    ], style={"display": "none"})
])

# 3. РОУТИНГ
@app.callback(
    [Output('page-content', 'children'),
     Output('app-header', 'style'),
     Output('bottom-action-bar', 'style')],
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/' or pathname is None:
        return auth_layout(), {"display": "none"}, {"display": "none"}

    elif pathname == '/select-role':
        return create_role_selection_layout(), {"display": "flex"}, {"display": "none"}

    # ПОЛЕВОЙ РЕЖИМ
    elif pathname == '/bha':
        return bha_assembly_layout(), {"display": "flex"}, {"display": "flex"}
    elif pathname == '/mud':
        return create_mud_control_layout(), {"display": "flex"}, {"display": "none"}
    elif pathname == '/trajectory':
        return create_trajectory_layout(), {"display": "flex"}, {"display": "none"}
    elif pathname == '/compliance':
        return create_compliance_layout(), {"display": "flex"}, {"display": "none"}
    elif pathname == '/telemetry-demo':
        return create_telemetry_demo_layout(), {"display": "flex"}, {"display": "none"}
    elif pathname == '/resistivity-control':
        return create_resistivity_control_layout(), {"display": "flex"}, {"display": "none"}
    elif pathname == '/telemetry-system':
        return create_telemetry_system_layout(), {"display": "flex"}, {"display": "none"}

    # ОФИСНЫЙ РЕЖИМ
    elif pathname == '/kb-admin':
        return create_kb_admin_layout(), {"display": "flex"}, {"display": "none"}
    elif pathname == '/stress-test':
        return create_stress_test_layout(), {"display": "flex"}, {"display": "none"}
    elif pathname == '/sync':
        return html.Div([
            html.H3("Модуль синхронизации данных", className="mt-4"),
            html.P("Интерфейс трехуровневой синхронизации (буровая ↔ офис ↔ буровая) находится в разработке.")
        ]), {"display": "flex"}, {"display": "none"}

    else:
        return html.Div([
            html.H3("404: Страница не найдена", className="mt-4"),
            dbc.Button("Вернуться к выбору роли", href="/select-role", color="primary")
        ]), {"display": "flex"}, {"display": "none"}

# 4. РЕГИСТРАЦИЯ CALLBACK'ов
auth_callbacks(app, data_bridge)
role_selection_callbacks(app, data_bridge)
bha_assembly_callbacks(app, data_bridge)
mud_control_callbacks(app, data_bridge)
trajectory_forecast_callbacks(app, data_bridge)
compliance_checklist_callbacks(app, data_bridge)
telemetry_demo_callbacks(app, data_bridge)
resistivity_control_callbacks(app, data_bridge)
telemetry_system_callbacks(app, data_bridge)
kb_admin_callbacks(app, data_bridge)
stress_test_callbacks(app, data_bridge)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
