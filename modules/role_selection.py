"""
СТРАНИЦА ВЫБОРА РОЛИ ПОЛЬЗОВАТЕЛЯ
"""
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

def create_role_selection_layout():
    return html.Div([
        html.Div([
            html.H1("Выберите режим работы", style={"color": "white", "margin": "0"}),
            html.P("Drilling Assistant | Система контроля буровых работ", style={"color": "#BFDBFE", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], className="module-header"),

        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div("🛠️", style={"fontSize": "80px", "marginBottom": "20px"}),
                    html.H3("Полевой режим", style={"color": "#1E40AF", "marginBottom": "15px"}),
                    html.P("Работа на буровой: контроль параметров, чек-листы, акты", style={"color": "#64748B", "marginBottom": "20px", "fontSize": "14px"}),
                    dbc.Button("Перейти в полевой режим", id='btn-field-mode', color="primary", size="lg", className="w-100", style={"fontWeight": "bold", "padding": "15px"})
                ], style={"backgroundColor": "white", "padding": "40px", "borderRadius": "12px", "border": "2px solid #E2E8F0", "textAlign": "center", "height": "100%", "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"})
            ], width=6, className="mb-4"),
            dbc.Col([
                html.Div([
                    html.Div("⚙️", style={"fontSize": "80px", "marginBottom": "20px"}),
                    html.H3("Офисный режим", style={"color": "#1E40AF", "marginBottom": "15px"}),
                    html.P("Управление базой знаний, синхронизация, администрирование", style={"color": "#64748B", "marginBottom": "20px", "fontSize": "14px"}),
                    dbc.Button("Перейти в офисный режим", id='btn-office-mode', color="success", size="lg", className="w-100", style={"fontWeight": "bold", "padding": "15px"})
                ], style={"backgroundColor": "white", "padding": "40px", "borderRadius": "12px", "border": "2px solid #E2E8F0", "textAlign": "center", "height": "100%", "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"})
            ], width=6, className="mb-4"),
        ], className="mt-4"),
    ], style={"padding": "40px", "maxWidth": "1000px", "margin": "0 auto"})

def role_selection_callbacks(app, data_bridge):
    @app.callback(
        Output('url', 'pathname'),
        [Input('btn-field-mode', 'n_clicks'), Input('btn-office-mode', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_role_selection(field_clicks, office_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'btn-field-mode':
            return '/bha'
        elif button_id == 'btn-office-mode':
            return '/kb-admin'
        return dash.no_update
