"""
МОДУЛЬ: СБОРКА КНБК И ВХОДНОЙ КОНТРОЛЬ
Объединяет входной контроль элементов, проверку ВЗД, УМК, склад и оценку рисков.
"""
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash_table
import pandas as pd

# Импорты всех подмодулей
from modules.warehouse import create_warehouse_upload_section, create_alternative_suggestion, warehouse_callbacks
from modules.ai_advisor import create_ai_advisor_panel, ai_advisor_callbacks
from modules.bha_umk_enhanced import create_umk_enhanced_panel, umk_enhanced_callbacks
from modules.bha_joints import get_joints_table_component
from modules.bha_visual import create_bha_visualization
from modules.vzd_wear import create_vzd_wear_panel, vzd_wear_callbacks
from modules.risk_assessment import create_risk_assessment_panel, risk_assessment_callbacks
from utils.data_bridge import DataBridge

# --- ДАННЫЕ ДЛЯ ПРИМЕРА (Имитация парсинга рапорта) ---
sample_bha_data = pd.DataFrame([
    {"№": 1, "Элемент": "ТБТ-172", "OD факт": 171.5, "OD ном": 172.0, "Статус": "ОК"},
    {"№": 2, "Элемент": "Переводник 172/165", "OD факт": 171.8, "OD ном": 172.0, "Статус": "ОК"},
    {"№": 3, "Элемент": "ВЗД-172 (Радиус)", "OD факт": 171.2, "OD ном": 172.0, "Статус": "Требует проверки"},
    {"№": 4, "Элемент": "НУБТ-165", "OD факт": 164.5, "OD ном": 165.0, "Статус": "ОК"},
])

# ============================================================================
# ЛЕЙАУТ МОДУЛЯ
# ============================================================================

def bha_assembly_layout():
    """Основной макет модуля сборки КНБК (вызывается из app.py)"""
    return html.Div([
        dbc.Row([
            dbc.Col(width=9, children=[
                dcc.Tabs(
                    id='main-tabs',
                    value='tab-input',
                    className='custom-tabs',
                    children=[
                        dcc.Tab(label='1. Входной контроль элементов', value='tab-input'),
                        dcc.Tab(label='2. Визуальная схема и стыки', value='tab-visual'),
                        dcc.Tab(label='3. Расчет УМК и натяжения', value='tab-umk'),
                        dcc.Tab(label='4. Живой склад', value='tab-warehouse'),
                        dcc.Tab(label='5. Оценка рисков', value='tab-risks'),
                    ]
                ),
                html.Div(id='tabs-content', className="mt-3")
            ]),
            dbc.Col(width=3, children=[
                html.Div(className="right-panel", children=[
                    html.Div(className="panel-title", children="КОНТРОЛЬ ИЗНОСА ВЗД"),
                    html.Div(id='vzd-panel-content')
                ])
            ])
        ])
    ])

def get_input_control_tab():
    """Вкладка 1: Входной контроль (Таблица элементов)"""
    return html.Div([
        html.H4("Журнал входного контроля элементов КНБК", 
                style={"color": "#0f172a", "borderBottom": "2px solid #cbd5e1", "paddingBottom": "10px"}),
        html.P("Внесите фактические замеры по каждому элементу согласно паспорту.", style={"color": "#64748b"}),
        
        dash_table.DataTable(
            id='bha-input-table',
            columns=[
                {"name": "№", "id": "№"},
                {"name": "Элемент", "id": "Элемент"},
                {"name": "OD факт (мм)", "id": "OD факт", "type": "numeric", "editable": True},
                {"name": "OD ном (мм)", "id": "OD ном", "type": "numeric"},
                {"name": "Статус СМК", "id": "Статус"},
            ],
            data=sample_bha_data.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'border': '1px solid #e2e8f0'},
            style_header={'backgroundColor': '#f1f5f9', 'fontWeight': 'bold', 'color': '#0f172a'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Статус} = "Требует проверки"'},
                    'backgroundColor': '#fef2f2',
                    'color': '#dc2626',
                    'fontWeight': 'bold'
                },
                {
                    'if': {'filter_query': '{Статус} = "ОК"'},
                    'backgroundColor': '#f0fdf4',
                    'color': '#16a34a'
                }
            ]
        ),
        
        html.Div(style={"marginTop": "20px"}, children=[
            html.Button("Добавить элемент", className="action-btn btn-outline", style={"marginRight": "10px"}),
            html.Button("Загрузить из рапорта (Excel/CSV)", className="action-btn btn-primary")
        ])
    ])

def get_visual_tab():
    """Вкладка 2: Визуальная схема + Таблица стыков"""
    fig = create_bha_visualization()
    
    return html.Div([
        html.H4("Визуальная схема КНБК (Топология)", 
                style={"color": "#0f172a", "marginBottom": "15px", "borderBottom": "2px solid #cbd5e1", "paddingBottom": "10px"}),
        
        dcc.Graph(
            id='bha-visual-graph', 
            figure=fig,
            config={'displayModeBar': False}
        ),
        
        html.Hr(style={"borderColor": "#cbd5e1", "margin": "25px 0"}),
        
        html.H5("Таблица стыков и перепадов диаметров", 
                style={"color": "#0f172a", "marginTop": "20px", "marginBottom": "15px"}),
        
        get_joints_table_component(),
    ])

def get_umk_tab():
    """Вкладка 3: УМК"""
    return create_umk_enhanced_panel()

def get_warehouse_tab():
    """Вкладка 4: Живой склад"""
    return create_warehouse_upload_section()

def get_risks_tab():
    """Вкладка 5: Оценка рисков"""
    return create_risk_assessment_panel()

def get_vzd_panel():
    """Правая панель: Контроль ВЗД (Всегда видна)"""
    return create_vzd_wear_panel()

# ============================================================================
# CALLBACKS (ЛОГИКА)
# ============================================================================

def bha_assembly_callbacks(app, data_bridge):
    """Регистрирует ВСЕ callback'и модуля сборки КНБК"""
    
    # 1. Регистрируем callback'и всех подмодулей
    vzd_wear_callbacks(app, data_bridge)
    umk_enhanced_callbacks(app, data_bridge)
    ai_advisor_callbacks(app, data_bridge)
    warehouse_callbacks(app, data_bridge)
    risk_assessment_callbacks(app, data_bridge)
    
    # 2. Переключение вкладок
    @app.callback(
        Output('tabs-content', 'children'),
        Input('main-tabs', 'value')
    )
    def render_tab_content(tab_value):
        if tab_value == 'tab-input':
            return get_input_control_tab()
        elif tab_value == 'tab-visual':
            return get_visual_tab()
        elif tab_value == 'tab-umk':
            return get_umk_tab()
        elif tab_value == 'tab-warehouse':
            return get_warehouse_tab()
        elif tab_value == 'tab-risks':
            return get_risks_tab()
        return html.Div("Выберите вкладку")
    
    # 3. Инициализация правой панели при загрузке
    @app.callback(
        Output('vzd-panel-content', 'children'),
        Input('main-tabs', 'value')
    )
    def init_vzd_panel(_):
        return get_vzd_panel()
