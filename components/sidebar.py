"""
БОКОВОЕ МЕНЮ НАВИГАЦИИ
Корпоративный стиль 2024
"""
from dash import html
import dash_bootstrap_components as dbc

def create_sidebar():
    return html.Div([
        html.H4("Drilling Assistant", className="text-center mt-3 mb-4",
                style={"fontWeight": "700", "letterSpacing": "1px", "color": "#1E40AF"}),

        dbc.Nav([
            dbc.NavLink("Вход в систему", href="/", active="exact"),
            dbc.NavLink("Сборка КНБК и ВЗД", href="/bha", active="exact"),
            dbc.NavLink("Контроль растворов", href="/mud", active="exact"),
            dbc.NavLink("Прогноз траектории", href="/trajectory", active="exact"),
            dbc.NavLink("Контроль резака", href="/resistivity-control", active="exact"),
            dbc.NavLink("ТС в КНБК", href="/telemetry-system", active="exact"),
            dbc.NavLink("Комплаенс и ЛНД", href="/compliance", active="exact"),
            dbc.NavLink("Демо: Телеметрия", href="/telemetry-demo", active="exact"),
            dbc.NavLink("Управление БЗ", href="/kb-admin", active="exact"),
            dbc.NavLink("Стресс-тест", href="/stress-test", active="exact"),
            dbc.NavLink("Синхронизация", href="/sync", active="exact"),
        ], vertical=True, pills=True, className="px-3"),

        html.Hr(className="my-4"),

        html.Div(id='sidebar-context', children=[
            html.H6("Контекст КНБК", className="px-3 text-muted small text-uppercase"),
            html.P("Инженер: Иванов И.И.", className="px-3 small mb-1", id='sidebar-engineer'),
            html.P("Скважина: Приобское №101", className="px-3 small mb-1", id='sidebar-well'),
            html.P("ВЗД: № 6677", className="px-3 small", id='sidebar-vzd'),
        ]),

        html.Hr(className="my-4"),

        dbc.Button("Выйти из системы",
                   color="danger",
                   className="w-100 mx-3",
                   id='btn-logout')
    ], className="vh-100 bg-light border-end")
