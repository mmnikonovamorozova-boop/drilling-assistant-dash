"""
СТРАНИЦА ВЫБОРА РОЛИ ПОЛЬЗОВАТЕЛЯ
Полевой инженер vs Администратор БЗ
"""
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc


def create_role_selection_layout():
    """Страница выбора режима работы"""
    return html.Div([
        # Заголовок
        html.Div([
            html.H1("Выберите режим работы", style={"color": "white", "margin": "0"}),
            html.P("Drilling Assistant | Система контроля буровых работ", 
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "30px", "borderRadius": "8px", "marginBottom": "30px", "textAlign": "center"}),
        
        # Две большие кнопки выбора
        dbc.Row([
            # Полевой режим
            dbc.Col([
                html.Div([
                    html.Div("🛠️", style={"fontSize": "80px", "marginBottom": "20px"}),
                    html.H3("Полевой режим", style={"color": "#0F172A", "marginBottom": "15px"}),
                    html.P("Работа на буровой: контроль параметров, чек-листы, акты", 
                          style={"color": "#64748B", "marginBottom": "20px", "fontSize": "14px"}),
                    dbc.Button("Перейти в полевой режим", 
                              id='btn-field-mode',
                              color="primary",
                              size="lg",
                              className="w-100",
                              style={"fontWeight": "bold", "padding": "15px"})
                ], style={
                    "backgroundColor": "white",
                    "padding": "40px",
                    "borderRadius": "12px",
                    "border": "2px solid #E2E8F0",
                    "textAlign": "center",
                    "height": "100%",
                    "transition": "all 0.3s ease",
                    "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
                })
            ], width=6, className="mb-4"),
            
            # Офисный режим
            dbc.Col([
                html.Div([
                    html.Div("⚙️", style={"fontSize": "80px", "marginBottom": "20px"}),
                    html.H3("Офисный режим", style={"color": "#0F172A", "marginBottom": "15px"}),
                    html.P("Управление базой знаний, синхронизация, администрирование", 
                          style={"color": "#64748B", "marginBottom": "20px", "fontSize": "14px"}),
                    dbc.Button("Перейти в офисный режим", 
                              id='btn-office-mode',
                              color="success",
                              size="lg",
                              className="w-100",
                              style={"fontWeight": "bold", "padding": "15px"})
                ], style={
                    "backgroundColor": "white",
                    "padding": "40px",
                    "borderRadius": "12px",
                    "border": "2px solid #E2E8F0",
                    "textAlign": "center",
                    "height": "100%",
                    "transition": "all 0.3s ease",
                    "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
                })
            ], width=6, className="mb-4"),
        ], className="mt-4"),
        
        # Информация о текущем пользователе
        html.Div([
            html.Hr(),
            html.P([
                html.Span("Текущий пользователь: ", style={"color": "#64748B"}),
                html.Span(id='current-user-info', style={"fontWeight": "bold", "color": "#0F172A"})
            ], style={"textAlign": "center", "fontSize": "14px"})
        ], style={"marginTop": "30px"})
    ], style={"padding": "40px", "maxWidth": "1000px", "margin": "0 auto"})


def role_selection_callbacks(app, data_bridge):
    """Callback'ы для выбора роли"""
    
    @app.callback(
        Output('url', 'pathname'),
        [Input('btn-field-mode', 'n_clicks'),
         Input('btn-office-mode', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_role_selection(field_clicks, office_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'btn-field-mode':
            return '/bha'  # Переход к полевым модулям
        elif button_id == 'btn-office-mode':
            return '/kb-admin'  # Переход к администрированию
        
        return dash.no_update
