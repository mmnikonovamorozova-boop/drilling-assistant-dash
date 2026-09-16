"""
МОДУЛЬ АВТОРИЗАЦИИ
Страница входа в систему с перенаправлением на выбор роли
"""
import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime

def auth_layout():
    """Макет страницы авторизации"""
    return html.Div([
        # Скрытый компонент для управления роутингом после входа
        dcc.Location(id='auth-redirect-url', refresh=False),
        
        html.Div([
            html.H2("Вход в систему", className="text-center mb-4", style={"color": "#0f172a", "fontWeight": "700"}),
            html.P("Drilling Assistant | Промышленный стандарт", className="text-center text-muted mb-4"),
            
            dbc.Card([
                dbc.CardBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Имя пользователя", style={"fontWeight": "bold"}),
                                dbc.Input(
                                    id='auth-username', 
                                    type='text', 
                                    placeholder='Например: user или admin', 
                                    className="mb-3",
                                    value="user" # Для удобства тестирования
                                )
                            ], width=12),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Пароль", style={"fontWeight": "bold"}),
                                dbc.Input(
                                    id='auth-password', 
                                    type='password', 
                                    placeholder='Введите пароль', 
                                    className="mb-3",
                                    value="1234" # Для удобства тестирования
                                )
                            ], width=12),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "Войти в систему", 
                                    id='auth-login-btn', 
                                    color="primary", 
                                    className="w-100", 
                                    size="lg",
                                    style={"fontWeight": "bold", "marginTop": "10px"}
                                )
                            ], width=12),
                        ]),
                        html.Div(id='auth-error-msg', className="text-danger mt-3 text-center", style={"fontWeight": "bold"})
                    ])
                ])
            ], className="shadow-sm", style={"borderRadius": "12px", "border": "1px solid #e2e8f0"})
        ], style={"maxWidth": "450px", "margin": "80px auto", "padding": "20px"})
    ])

def auth_callbacks(app, data_bridge):
    """Callback'и для обработки входа"""
    
    @app.callback(
        Output('auth-redirect-url', 'pathname'), # Перенаправляем главный роутер
        Output('auth-error-msg', 'children'),
        Input('auth-login-btn', 'n_clicks'),
        [State('auth-username', 'value'),
         State('auth-password', 'value')],
        prevent_initial_call=True
    )
    def handle_login(n_clicks, username, password):
        if not username or not password:
            return dash.no_update, "Пожалуйста, заполните все поля."
        
        # Простая проверка для демонстрации (в реальности здесь будет запрос к БД или LDAP)
        # Допустимые тестовые пары: user/1234 или admin/1234
        if username.lower() in ['admin', 'user', 'инженер'] and password == '1234':
            
            # Здесь можно сохранить данные сессии в data_bridge
            # data_bridge.set_session_data({'user': username, 'login_time': datetime.now().isoformat()})
            
            # Перенаправляем на страницу выбора роли
            return '/select-role', ""
        else:
            return dash.no_update, "Неверное имя пользователя или пароль. (Попробуйте: user / 1234)"
