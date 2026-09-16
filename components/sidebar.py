"""
БОКОВОЕ МЕНЮ НАВИГАЦИИ
"""
from dash import html
import dash_bootstrap_components as dbc

def create_sidebar():
    """Создает боковое меню с навигацией"""
    return html.Div([
        # Логотип / Заголовок
        html.H4("🛢️ Drilling Assistant", className="text-center mt-3 mb-4"),
        
        # Меню навигации
        dbc.Nav([
            dbc.NavLink("🔐 Вход в систему", href="/", active="exact"),
            dbc.NavLink("🧪 Контроль раствора", href="/fluid", active="exact"),
            dbc.NavLink("🔧 Виртуальный ротор", href="/rotor", active="exact"),
            dbc.NavLink("📊 Модуль 3", href="/module3", active="exact"),
            dbc.NavLink("📈 Модуль 4", href="/module4", active="exact"),
        ], vertical=True, pills=True, className="px-3"),
        
        html.Hr(),
        
        # Контекст КНБК (динамически обновляется)
        html.Div(id='sidebar-context', children=[
            html.H6("🌐 Контекст КНБК №1", className="px-3"),
            html.P("ФИО Инженера: Иванов И.И.", className="px-3 small"),
            html.P("Серийный номер ВЗД: № 6677", className="px-3 small"),
        ]),
        
        html.Hr(),
        
        # Кнопка выхода
        dbc.Button("🚪 Выйти из системы", 
                   color="danger", 
                   className="w-100 mx-3")
    ], className="vh-100")
dbc.NavLink("💾 Синхронизация", href="/sync", active="exact"),
dbc.NavLink("🏢 Офисная синхронизация", href="/office-sync", active="exact"),
dbc.NavLink(" Контроль растворов", href="/mud", active="exact"),
