"""
МОДУЛЬ: СБОРКА КНБК И ВХОДНОЙ КОНТРОЛЬ
Объединяет входной контроль элементов и проверку ВЗД.
"""
from modules.bha_visual import create_bha_visualization
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash_table
import pandas as pd

# --- ДАННЫЕ ДЛЯ ПРИМЕРА (Имитация парсинга рапорта) ---
# В будущем это будет приходить из data_bridge после загрузки файла
sample_bha_data = pd.DataFrame([
    {"№": 1, "Элемент": "ТБТ-172", "OD факт": 171.5, "OD ном": 172.0, "Статус": "ОК"},
    {"№": 2, "Элемент": "Переводник 172/165", "OD факт": 171.8, "OD ном": 172.0, "Статус": "ОК"},
    {"№": 3, "Элемент": "ВЗД-172 (Радиус)", "OD факт": 171.2, "OD ном": 172.0, "Статус": "Требует проверки"},
    {"№": 4, "Элемент": "НУБТ-165", "OD факт": 164.5, "OD ном": 165.0, "Статус": "ОК"},
])

# --- ЛЕЙАУТ (ВНЕШНИЙ ВИД) ---

def get_input_control_tab():
    """Вкладка 1: Входной контроль (Таблица элементов)"""
    return html.Div([
        html.H4("Журнал входного контроля элементов КНБК", style={"color": "#0f172a", "borderBottom": "2px solid #cbd5e1", "paddingBottom": "10px"}),
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
    """Вкладка 2: Визуальная схема (Plotly)"""
    fig = create_bha_visualization()
    
    return html.Div([
        html.H4("Визуальная схема КНБК (Топология)", style={"color": "#0f172a", "marginBottom": "15px"}),
        # Вставляем интерактивный график
        dcc.Graph(
            id='bha-visual-graph', 
            figure=fig,
            config={'displayModeBar': False} # Убираем лишние кнопки Plotly для чистоты
        ),
        
        html.Hr(style={"borderColor": "#cbd5e1"}),
        
        html.H5("Таблица стыков и перепадов диаметров", style={"color": "#0f172a", "marginTop": "20px"}),
        # Здесь потом будет детальная таблица стыков
        html.Div("Данные по стыкам загружаются...", style={"color": "#64748b"})
    ]) 

def get_umk_tab():
    """Вкладка 3: УМК (Заглушка)"""
    return html.Div([
        html.H4("Расчет усилий натяжения ключа УМК", style={"color": "#0f172a"}),
        html.P("Модуль расчета моментов затяжки.", style={"color": "#64748b"})
    ])

def get_vzd_panel():
    """Правая панель: Контроль ВЗД (Всегда видна)"""
    return html.Div([
        # Блок ввода
        html.Label("Размер 'А' (мм):", style={"fontSize": "12px", "fontWeight": "bold"}),
        dcc.Input(id='vzd-size-a', type='number', value=10.00, style={"width": "100%", "marginBottom": "10px", "padding": "5px"}),
        
        html.Label("Размер 'Б' (мм):", style={"fontSize": "12px", "fontWeight": "bold"}),
        dcc.Input(id='vzd-size-b', type='number', value=5.50, style={"width": "100%", "marginBottom": "10px", "padding": "5px"}),
        
        html.Label("Радиальный люфт ИЧ (мм):", style={"fontSize": "12px", "fontWeight": "bold"}),
        dcc.Input(id='vzd-radial', type='number', value=0.20, step=0.05, style={"width": "100%", "marginBottom": "15px", "padding": "5px"}),
        
        # Блок расчета
        html.Div(className="metric-card", children=[
            html.Div(className="metric-label", children="ОСЕВОЙ ЛЮФТ"),
            html.Div(id='vzd-axial-result', className="metric-value", children="4.50 мм", style={"color": "#dc2626"})
        ]),
        
        html.Div(className="metric-card", children=[
            html.Div(className="metric-label", children="ЛИМИТ (Паспорт/ТК)"),
            html.Div(className="metric-value", children="3.00 мм", style={"fontSize": "18px"})
        ]),
        
        # Вердикт
        html.Div(id='vzd-verdict-box', className="verdict-box verdict-reject", children=[
            "ВЗД ОТБРАКОВАН",
            html.Br(),
            html.Span("Спуск запрещен", style={"fontSize": "12px", "fontWeight": "normal"})
        ])
    ])

# --- CALLBACKS (ЛОГИКА) ---

def bha_assembly_callbacks(app, data_bridge):
    
    # 1. Переключение вкладок
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
        return html.Div("Выберите вкладку")

    # 2. Инициализация правой панели при загрузке
    @app.callback(
        Output('vzd-panel-content', 'children'),
        Input('main-tabs', 'value') # Срабатывает при старте
    )
    def init_vzd_panel(_):
        return get_vzd_panel()

    # 3. Живой расчет люфта ВЗД (Drill-down логика)
    @app.callback(
        [Output('vzd-axial-result', 'children'),
         Output('vzd-axial-result', 'style'),
         Output('vzd-verdict-box', 'children'),
         Output('vzd-verdict-box', 'className'),
         Output('metric-vzd-status', 'children'),
         Output('metric-vzd-status', 'style')],
        [Input('vzd-size-a', 'value'),
         Input('vzd-size-b', 'value')]
    )
    def calculate_vzd_wear(size_a, size_b):
        if size_a is None or size_b is None:
            return "0.00 мм", {}, "ОЖИДАНИЕ ДАННЫХ", "verdict-box", "ОЖИДАНИЕ", {}
        
        axial_play = size_a - size_b
        limit = 3.00 # Лимит ТК (например, Роснефть)
        
        # Форматирование значения
        val_str = f"{axial_play:.2f} мм"
        
        # Логика вердикта
        if axial_play >= limit:
            # ОТБРАКОВКА
            verdict_text = [
                "ВЗД ОТБРАКОВАН",
                html.Br(),
                html.Span(f"Люфт {val_str} > лимит {limit:.2f} мм", style={"fontSize": "12px", "fontWeight": "normal"})
            ]
            verdict_class = "verdict-box verdict-reject"
            style_val = {"color": "#dc2626"}
            status_text = "ОТБРАКОВАН"
            status_style = {"color": "#dc2626", "fontWeight": "bold"}
        else:
            # НОРМА
            verdict_text = [
                "ВЗД ДОПУЩЕН",
                html.Br(),
                html.Span(f"Люфт {val_str} < лимит {limit:.2f} мм", style={"fontSize": "12px", "fontWeight": "normal"})
            ]
            verdict_class = "verdict-box verdict-approve"
            style_val = {"color": "#16a34a"}
            status_text = "ДОПУЩЕН"
            status_style = {"color": "#16a34a", "fontWeight": "bold"}
            
        return val_str, style_val, verdict_text, verdict_class, status_text, status_style
