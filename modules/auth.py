"""
МОДУЛЬ АВТОРИЗАЦИИ И РЕГИСТРАЦИИ РЕЙСА
"""
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

def auth_layout():
    """Макет страницы авторизации"""
    return html.Div([
        html.H1("🔐 Вход в систему и регистрация рейса", className="mb-4"),
        html.P("Введите корпоративные учетные данные СМК и параметры текущих работ"),
        
        # Блок 1: Учетные данные
        dbc.Card([
            dbc.CardHeader(html.H3("🔑 Учетные данные")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Логин:"),
                        dbc.Input(id='login-input', type='text', placeholder='Введите логин')
                    ], width=6),
                    dbc.Col([
                        html.Label("Пароль:"),
                        dbc.Input(id='password-input', type='password', placeholder='Введите пароль')
                    ], width=6)
                ])
            ])
        ], className="mb-4"),
        
        # Блок 2: Регистрация параметров
        dbc.Card([
            dbc.CardHeader(html.H3("📋 Регистрация параметров полевой партии (СТО ИНТИ)")),
            dbc.CardBody([
                html.Label("ФИО ответственного инженера по ННБ / ТМС:"),
                dbc.Input(id='engineer-name-input', type='text', placeholder='Иванов И.И.', className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Номер скважины / Кустовая площадка:"),
                        dbc.Input(id='well-number-input', type='text', placeholder='Скв. № 101, Куст 5')
                    ], width=4),
                    dbc.Col([
                        html.Label("Название месторождения:"),
                        dbc.Input(id='field-name-input', type='text', placeholder='Приобское')
                    ], width=4),
                    dbc.Col([
                        html.Label("Порядковый номер сборки КНБК:"),
                        dbc.Input(id='bha-number-input', type='text', value='1')
                    ], width=4)
                ])
            ])
        ], className="mb-4"),
        
        # Блок 3: Привязка к контракту
        dbc.Card([
            dbc.CardHeader(html.H3("🏢 Привязка к контракту Заказчика:")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Холдинг / Оператор (ВИНК):"),
                        dbc.Select(
                            id='company-select',
                            options=[
                                {"label": "Газпром (Газовые ДО)", "value": "Газпром"},
                                {"label": "Роснефть", "value": "Роснефть"},
                                {"label": "ЛУКОЙЛ", "value": "ЛУКОЙЛ"},
                                {"label": "НОВАТЭК", "value": "НОВАТЭК"}
                            ],
                            value="Газпром"
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Конкретное предприятие (Заказчик):"),
                        dbc.Select(
                            id='client-select',
                            options=[
                                {"label": "ООО Газпром добыча Уренгой", "value": "Газпром добыча Уренгой"},
                                {"label": "ПАО НК Роснефть", "value": "Роснефть"},
                            ],
                            value="Газпром добыча Уренгой"
                        )
                    ], width=6)
                ])
            ])
        ], className="mb-4"),
        
        # Кнопка авторизации
        dbc.Button(" Авторизоваться и запустить систему", 
                   id='auth-button', 
                   color="primary", 
                   className="w-100 mb-3"),
        
        # Уведомления
        html.Div(id='auth-output')
    ])

def auth_callbacks(app, data_bridge):
    """Регистрирует callback'и для модуля авторизации"""
    
    @app.callback(
        Output('auth-output', 'children'),
        Input('auth-button', 'n_clicks'),
        State('engineer-name-input', 'value'),
        State('well-number-input', 'value'),
        State('field-name-input', 'value'),
        State('bha-number-input', 'value'),
        State('company-select', 'value'),
        prevent_initial_call=True
    )
    def handle_auth(n_clicks, engineer, well, field, bha, company):
        if n_clicks is None:
            return None
        
        # Валидация
        if not engineer or not well or not field:
            return dbc.Alert("Заполните все обязательные поля!", color="danger")
        
        # Сохраняем данные в шлюз
        data_bridge.update_from_dict({
            'engineer_name': engineer,
            'well_number': well,
            'field_name': field,
            'bha_number': bha,
            'company_choice': company
        })
        
        return dbc.Alert("✅ Авторизация успешна! Добро пожаловать.", color="success")
