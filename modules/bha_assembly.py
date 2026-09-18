"""
МОДУЛЬ СБОРКИ КНБК И ВХОДНОГО КОНТРОЛЯ ВЗД
Все компоненты создаются СРАЗУ в макете
"""
import pandas as pd
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash_table

from modules.bha_umk_enhanced import create_umk_enhanced_panel, umk_enhanced_callbacks
from modules.bha_joints import get_joints_table_component
from modules.vzd_wear import create_vzd_wear_panel, vzd_wear_callbacks

sample_bha_data = [
    {"Наименование": "ТБТ-172", "S/N": "ТБТ-001", "OD": 172.0, "ID": 71.4, "Длина": 9.2, "Статус": "✅ OK"},
    {"Наименование": "Переводник 172/165", "S/N": "ПП-045", "OD": 172.0, "ID": 71.4, "Длина": 1.5, "Статус": "✅ OK"},
    {"Наименование": "НУБТ-165", "S/N": "НУБТ-112", "OD": 165.0, "ID": 71.4, "Длина": 9.1, "Статус": "✅ OK"},
    {"Наименование": "УЗС-165", "S/N": "УЗС-009", "OD": 165.0, "ID": 71.4, "Длина": 8.9, "Статус": "✅ OK"},
    {"Наименование": "Пульсатор-165", "S/N": "ПУЛ-023", "OD": 165.0, "ID": 71.4, "Длина": 3.2, "Статус": "✅ OK"},
    {"Наименование": "Фильтр-165", "S/N": "ФИЛ-007", "OD": 165.0, "ID": 71.4, "Длина": 2.1, "Статус": "✅ OK"},
    {"Наименование": "ВЗД-172", "S/N": "ВЗД-6677", "OD": 172.0, "ID": 120.0, "Длина": 8.5, "Статус": "✅ OK"},
]

def bha_assembly_layout():
    return html.Div([
        html.Div([
            html.H2("Сборка КНБК и входной контроль ВЗД", style={"color": "white", "margin": "0"}),
            html.P("Проверка сертификатов, расчет УМК, контроль стыков", style={"color": "#BFDBFE", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], className="module-header"),

        dcc.Tabs(id='bha-tabs', value='tab-input', className='custom-tabs', children=[
            dcc.Tab(label='Входной контроль', value='tab-input'),
            dcc.Tab(label='Расчет УМК', value='tab-umk'),
            dcc.Tab(label='Таблица стыков', value='tab-joints'),
            dcc.Tab(label='Контроль ВЗД', value='tab-vzd'),
        ]),

        # ВСЕ ВКЛАДКИ СОЗДАНЫ СРАЗУ
        html.Div(id='bha-input-tab', children=[
            html.H4("Таблица элементов КНБК", style={"color": "#1E40AF", "marginBottom": "15px", "marginTop": "20px"}),
            dash_table.DataTable(
                id='bha-elements-table',
                columns=[{"name": i, "id": i} for i in ["Наименование", "S/N", "OD", "ID", "Длина", "Статус"]],
                data=sample_bha_data,
                editable=True,
                style_table={'overflowX': 'auto', 'border': '1px solid #E2E8F0', 'borderRadius': '8px'},
                style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '13px'},
                style_header={'backgroundColor': '#1E40AF', 'fontWeight': 'bold', 'color': 'white'},
                style_data_conditional=[
                    {"if": {"filter_query": "{Статус} contains '✅'"}, "backgroundColor": "#D1FAE5", "color": "#065F46"},
                ]
            ),
            html.Div(id='bha-validation-summary', style={"marginTop": "20px"}),
        ], style={"marginTop": "20px"}),

        html.Div(id='bha-umk-tab', children=[
            create_umk_enhanced_panel(),
            html.Div(id='umk-results-enhanced'),
        ], style={"display": "none", "marginTop": "20px"}),

        html.Div(id='bha-joints-tab', children=[
            get_joints_table_component(),
        ], style={"display": "none", "marginTop": "20px"}),

        html.Div(id='bha-vzd-tab', children=[
            create_vzd_wear_panel(),
            html.Div(id='vzd-wear-results'),
        ], style={"display": "none", "marginTop": "20px"}),
    ])

def bha_assembly_callbacks(app, data_bridge):
    @app.callback(
        [Output('bha-input-tab', 'style'),
         Output('bha-umk-tab', 'style'),
         Output('bha-joints-tab', 'style'),
         Output('bha-vzd-tab', 'style')],
        Input('bha-tabs', 'value'),
        prevent_initial_call=True
    )
    def switch_bha_tab(tab):
        hidden = {"display": "none", "marginTop": "20px"}
        visible = {"display": "block", "marginTop": "20px"}
        if tab == 'tab-input':
            return visible, hidden, hidden, hidden
        elif tab == 'tab-umk':
            return hidden, visible, hidden, hidden
        elif tab == 'tab-joints':
            return hidden, hidden, visible, hidden
        elif tab == 'tab-vzd':
            return hidden, hidden, hidden, visible
        return hidden, hidden, hidden, hidden

    @app.callback(
        Output('bha-validation-summary', 'children'),
        Input('bha-elements-table', 'data'),
        prevent_initial_call=True
    )
    def validate_bha_elements(data):
        if not data:
            return html.Div()
        df = pd.DataFrame(data)
        errors = []
        if df['S/N'].duplicated().any():
            duplicates = df[df['S/N'].duplicated()]['S/N'].tolist()
            errors.append(f"❌ Найдены дубликаты S/N: {', '.join(duplicates)}")
        invalid_dims = df[df['OD'] <= df['ID']]
        if not invalid_dims.empty:
            errors.append(f"❌ Найдены элементы с OD <= ID: {invalid_dims['Наименование'].tolist()}")
        if errors:
            return html.Div([
                html.H5("Ошибки входного контроля:", style={"color": "#EF4444", "marginBottom": "10px"}),
                html.Ul([html.Li(err, style={"marginBottom": "5px"}) for err in errors])
            ], style={"backgroundColor": "#FEE2E2", "padding": "15px", "borderRadius": "6px", "border": "1px solid #EF4444"})
        return html.Div([
            html.H5("✅ Все элементы прошли входной контроль", style={"color": "#10B981", "marginBottom": "10px"}),
            html.P(f"Проверено элементов: {len(df)}", style={"color": "#065F46"})
        ], style={"backgroundColor": "#D1FAE5", "padding": "15px", "borderRadius": "6px", "border": "1px solid #10B981"})

    umk_enhanced_callbacks(app, data_bridge)
    vzd_wear_callbacks(app, data_bridge)
