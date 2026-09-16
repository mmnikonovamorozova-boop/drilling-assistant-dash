"""
ГЛАВНЫЙ ФАЙЛ ПРИЛОЖЕНИЯ
Drilling Assistant - Industrial Dashboard
Архитектура с разделением ролей: Полевой режим / Офисный режим
"""
import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

from utils.data_bridge import DataBridge
from components.sidebar import create_sidebar

# Импорт модулей и их layout/callback функций
from modules.auth import auth_layout, auth_callbacks
from modules.role_selection import create_role_selection_layout, role_selection_callbacks
from modules.bha_assembly import bha_assembly_layout, bha_assembly_callbacks
from modules.mud_control import create_mud_control_layout, mud_control_callbacks
from modules.compliance_checklist import create_compliance_layout, compliance_checklist_callbacks
from modules.trajectory_forecast import create_trajectory_layout, trajectory_forecast_callbacks
from modules.knowledge_base_admin import create_kb_admin_layout, kb_admin_callbacks
from modules.telemetry_demo import create_telemetry_demo_layout, telemetry_demo_callbacks

# 1. Инициализация приложения
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

# Глобальный шлюз данных
data_bridge = DataBridge()

# 2. МАКЕТ ПРИЛОЖЕНИЯ
app.layout = html.Div([
    # Главный роутер и хранилище сессии
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='session-data', storage_type='session'),
    
    # Верхняя шапка (скрывается на странице авторизации)
    html.Div(id='app-header', className="app-header", children=[
        html.Div([
            html.H1("Drilling Assistant", style={"fontSize": "20px", "margin": "0", "fontWeight": "700"}),
            html.Div("Промышленный стандарт контроля буровых работ", className="meta-info", style={"fontSize": "13px", "color": "#94a3b8"})
        ]),
        html.Div(className="meta-info", children=[
            html.Span("Пользователь: ", style={"color": "#fff"}),
            html.Span(id='header-user', children="Гость"),
        ])
    ]),

    # Основной контейнер
    dbc.Container(fluid=True, className="mt-4", children=[
        dbc.Row([
            # Боковое меню
            dbc.Col(create_sidebar(), width=2, className="bg-light border-end", style={"minHeight": "100vh"}),
            
            # Основная область контента (меняется динамически)
            dbc.Col(width=10, children=[
                html.Div(id='page-content')
            ])
        ])
    ]),

    # Нижняя панель действий (появляется только в рабочих модулях)
    html.Div(id='bottom-action-bar', className="bottom-action-bar", children=[
        html.Div(className="action-metrics", children=[
            html.Div([html.Span("СТАТУС СИСТЕМЫ: ", style={"color": "#94a3b8"}), html.Span("АКТИВНА", style={"color": "#16a34a", "fontWeight": "bold"})]),
        ]),
        html.Div(children=[
            html.Button("Сформировать отчет", className="action-btn btn-primary", style={"marginRight": "10px"}),
            html.Button("Справка", className="action-btn btn-outline"),
        ])
    ], style={"display": "none"}) # По умолчанию скрыта
])

# 3. РОУТИНГ (ПЕРЕКЛЮЧЕНИЕ СТРАНИЦ)
@app.callback(
    [Output('page-content', 'children'),
     Output('app-header', 'style'),
     Output('bottom-action-bar', 'style')],
    Input('url', 'pathname')
)
def display_page(pathname):
    # Страница авторизации
    if pathname == '/' or pathname is None:
        return auth_layout(), {"display": "none"}, {"display": "none"}
    
    # Страница выбора роли (после успешной авторизации)
    elif pathname == '/select-role':
        return create_role_selection_layout(), {"display": "flex"}, {"display": "none"}
    
    # ===== ПОЛЕВОЙ РЕЖИМ =====
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
    
    # ===== ОФИСНЫЙ РЕЖИМ (АДМИНИСТРИРОВАНИЕ) =====
    elif pathname == '/kb-admin':
        return create_kb_admin_layout(), {"display": "flex"}, {"display": "none"}
    
    elif pathname == '/sync':
        # Заглушка для модуля синхронизации
        return html.Div([
            html.H3("Модуль синхронизации данных", className="mt-4"),
            html.P("Интерфейс трехуровневой синхронизации (буровая ↔ офис ↔ буровая) находится в разработке.")
        ]), {"display": "flex"}, {"display": "none"}
    
    else:
        # Если путь неизвестен, показываем 404 или перенаправляем на выбор роли
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
kb_admin_callbacks(app, data_bridge)

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)
