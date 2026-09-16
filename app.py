"""
ГЛАВНЫЙ ФАЙЛ ПРИЛОЖЕНИЯ
Drilling Assistant - Industrial Dashboard
"""
import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

from utils.data_bridge import DataBridge
from components.sidebar import create_sidebar

# Импорт модулей и их layout/callback функций
from modules.auth import auth_layout, auth_callbacks
from modules.bha_assembly import bha_assembly_layout, bha_assembly_callbacks
from modules.mud_control import create_mud_control_layout, mud_control_callbacks
from modules.compliance_checklist import create_compliance_layout, compliance_checklist_callbacks
from modules.sync_interface import create_sync_panel, sync_callbacks

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
    # Хранилище сессии и роутер
    dcc.Store(id='session-data', storage_type='session'),
    dcc.Location(id='url', refresh=False),
    
    # Верхняя шапка (скрывается на странице авторизации)
    html.Div(id='app-header', className="app-header", children=[
        html.Div([
            html.H1("СИСТЕМА КОНТРОЛЯ СБОРКИ КНБК", style={"fontSize": "20px", "margin": "0"}),
            html.Div("СТО ИНТИ S.QS.7 | Промышленный стандарт", className="meta-info", style={"fontSize": "13px", "color": "#94a3b8"})
        ]),
        html.Div(className="meta-info", children=[
            html.Span("Инженер: ", style={"color": "#fff"}),
            html.Span(id='header-engineer', children="Не авторизован"),
            html.Span(" | Скважина: ", style={"color": "#fff", "marginLeft": "15px"}),
            html.Span(id='header-well', children="---"),
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
            html.Div([html.Span("РИСК РЕЙСА: ", style={"color": "#94a3b8"}), html.Span(id='metric-risk', children="23%", style={"color": "#16a34a", "fontWeight": "bold"})]),
            html.Div([html.Span("СТАТУС ВЗД: ", style={"color": "#94a3b8"}), html.Span(id='metric-vzd-status', children="ОЖИДАНИЕ", style={"color": "#6c757d", "fontWeight": "bold"})]),
        ]),
        html.Div(children=[
            html.Button("Сформировать акт СМК", className="action-btn btn-primary", style={"marginRight": "10px"}),
            html.Button("Экспорт данных", className="action-btn btn-outline"),
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
    if pathname == '/':
        # Страница авторизации: скрываем шапку и нижнюю панель
        return auth_layout(), {"display": "none"}, {"display": "none"}
    
    elif pathname == '/bha':
        return bha_assembly_layout(), {"display": "flex"}, {"display": "flex"}
    
    elif pathname == '/mud':
        return create_mud_control_layout(), {"display": "flex"}, {"display": "none"}
    
    elif pathname == '/compliance':
        return create_compliance_layout(), {"display": "flex"}, {"display": "none"}
    
    elif pathname == '/sync':
        return create_sync_panel(), {"display": "flex"}, {"display": "none"}
    
    else:
        return html.Div([html.H3("404: Страница не найдена", className="mt-4")]), {"display": "flex"}, {"display": "none"}

# 4. РЕГИСТРАЦИЯ CALLBACK'ов
auth_callbacks(app, data_bridge)
bha_assembly_callbacks(app, data_bridge)
mud_control_callbacks(app, data_bridge)
compliance_checklist_callbacks(app, data_bridge)
sync_callbacks(app, data_bridge)

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)
