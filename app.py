"""
ГЛАВНЫЙ ФАЙЛ ПРИЛОЖЕНИЯ
Запуск: python app.py
"""
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from modules.auth import auth_layout, auth_callbacks
from components.sidebar import create_sidebar
from utils.data_bridge import DataBridge

# Инициализация приложения с темой Bootstrap
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)

# Глобальный шлюз данных (сквозная сессия)
data_bridge = DataBridge()

# Макет приложения (Layout)
app.layout = html.Div([
    # Хранилище сессии (заменяет st.session_state)
    dcc.Store(id='session-data', storage_type='session'),
    
    # Основной контейнер
    dbc.Container([
        # Боковое меню
        dbc.Row([
            dbc.Col(create_sidebar(), width=3, className="bg-light"),
            
            # Основная область контента
            dbc.Col([
                dcc.Location(id='url', refresh=False),
                html.Div(id='page-content')
            ], width=9)
        ])
    ], fluid=True)
])

# Регистрируем callback'и из модулей
auth_callbacks(app, data_bridge)

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)
