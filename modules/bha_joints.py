"""
МОДУЛЬ РАСЧЕТА И ОТОБРАЖЕНИЯ СТЫКОВ КНБК
Таблица перепадов диаметров между элементами с цветовой индикацией.
"""
import pandas as pd
from dash import html
import dash_ag_grid as dag

# Пример данных КНБК (в будущем будет браться из DataBridge после входного контроля)
bha_elements_for_joints = [
    {"name": "ТБТ-172", "od": 172.0, "sn": "ТБТ-001"},
    {"name": "Переводник 172/165", "od": 172.0, "sn": "ПП-045"},
    {"name": "НУБТ-165", "od": 165.0, "sn": "НУБТ-112"},
    {"name": "УЗС-165", "od": 165.0, "sn": "УЗС-009"},
    {"name": "Пульсатор-165", "od": 165.0, "sn": "ПУЛ-023"},
    {"name": "Фильтр-165", "od": 165.0, "sn": "ФИЛ-007"},
    {"name": "ВЗД-172", "od": 172.0, "sn": "ВЗД-6677"},
]

# Допуск по СТО ИНТИ (критический перепад)
CRITICAL_DELTA_D = 10.0  # мм

def calculate_joints_table():
    """Рассчитывает таблицу стыков между элементами КНБК"""
    joints_data = []
    
    for i in range(len(bha_elements_for_joints) - 1):
        el_top = bha_elements_for_joints[i]
        el_bot = bha_elements_for_joints[i + 1]
        
        delta_d = abs(el_top["od"] - el_bot["od"])
        
        # Определяем статус
        if delta_d > CRITICAL_DELTA_D:
            status = "КРИТИЧЕСКИЙ ПЕРЕПАД"
            status_color = "#EF4444"  # Красный
        elif delta_d > 5.0:
            status = "Повышенный перепад"
            status_color = "#F59E0B"  # Оранжевый
        else:
            status = "в допуске"
            status_color = "#10B981"  # Зеленый
        
        joints_data.append({
            "Стык №": i + 1,
            "Элемент А": el_top["name"],
            "S/N А": el_top["sn"],
            "Элемент Б": el_bot["name"],
            "S/N Б": el_bot["sn"],
            "OD А (мм)": el_top["od"],
            "OD Б (мм)": el_bot["od"],
            "ΔD (мм)": round(delta_d, 1),
            "Допуск СТО": f"{CRITICAL_DELTA_D:.1f} мм",
            "Статус": status,
            "status_color": status_color
        })
    
    return pd.DataFrame(joints_data)

def get_joints_table_component():
    """Возвращает компонент таблицы стыков для Dash"""
    df_joints = calculate_joints_table()
    
    # Настройка колонок для AG Grid
    column_defs = [
        {"headerName": "Стык №", "field": "Стык №", "width": 80, "cellStyle": {"textAlign": "center"}},
        {"headerName": "Элемент А → Элемент Б", "field": "Элемент А", "width": 200},
        {"headerName": "", "field": "Элемент Б", "width": 200},
        {"headerName": "ΔD (мм)", "field": "ΔD (мм)", "width": 100, "cellStyle": {"textAlign": "center", "fontWeight": "bold"}},
        {"headerName": "Допуск СТО", "field": "Допуск СТО", "width": 120, "cellStyle": {"textAlign": "center"}},
        {"headerName": "Статус", "field": "Статус", "width": 180, "cellStyle": {"textAlign": "center", "fontWeight": "bold"}},
    ]
    
    # CSS для цветовой индикации строк
    row_style = {
        "styleConditions": [
            {
                "condition": "params.data['Статус'] === 'КРИТИЧЕСКИЙ ПЕРЕПАД'",
                "style": {"backgroundColor": "#FEE2E2", "color": "#991B1B"},
            },
            {
                "condition": "params.data['Статус'] === 'Повышенный перепад'",
                "style": {"backgroundColor": "#FEF3C7", "color": "#92400E"},
            },
            {
                "condition": "params.data['Статус'] === 'в допуске'",
                "style": {"backgroundColor": "#D1FAE5", "color": "#065F46"},
            },
        ],
        "defaultStyle": {"backgroundColor": "white"},
    }
    
    return html.Div([
        dag.AgGrid(
            id='joints-table',
            rowData=df_joints.to_dict('records'),
            columnDefs=column_defs,
            defaultColDef={"resizable": True, "sortable": True, "filter": True},
            style={"height": "300px", "width": "100%"},
            dashGridOptions={
                "rowHeight": 35,
                "headerHeight": 40,
                "domLayout": "normal",
                "rowStyle": row_style,
            },
        ),
        
        # Легенда
        html.Div(style={"marginTop": "15px", "fontSize": "12px", "color": "#64748b"}, children=[
            html.Span("Легенда: ", style={"fontWeight": "bold"}),
            html.Span("🟢 В допуске (ΔD ≤ 5 мм)  ", style={"color": "#10B981"}),
            html.Span(" Повышенный (5 < ΔD ≤ 10 мм)  ", style={"color": "#F59E0B"}),
            html.Span("🔴 Критический перепад (ΔD > 10 мм)", style={"color": "#EF4444"}),
        ])
    ])
