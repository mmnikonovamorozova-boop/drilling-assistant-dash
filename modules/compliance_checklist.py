"""
ИНТЕЛЛЕКТУАЛЬНЫЙ МОДУЛЬ КОМПЛАЕНСА И ГЕНЕРАЦИИ АЛГОРИТМОВ
Анализирует требования ЛНД, текущие параметры и генерирует персонализированные блок-схемы действий.
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.compliance_engine import get_compliance_engine

compliance = get_compliance_engine()

# ============================================================================
# БАЗА ЗНАНИЙ: ОПЕРАЦИИ + ТРЕБОВАНИЯ ЛНД + АЛГОРИТМЫ
# ============================================================================

OPERATIONAL_KB = {
    "Ликвидация дифференциального прихвата": {
        "description": "Алгоритм действий при дифференциальном прихвате бурильной колонны",
        "standard": "СТО ИНТИ S.QS.8, Р-ТС-21",
        "steps": [
            {
                "id": "1",
                "title": "Фиксация параметров прихвата",
                "action": "Зафиксировать вес инструмента на крюке, давление на стояке, объем прокачанного раствора",
                "responsible": "Инженер ННБ",
                "critical": False,
                "conditions": []
            },
            {
                "id": "2",
                "title": "Оценка критичности ситуации",
                "action": "Рассчитать силу прихвата и сравнить с допустимой нагрузкой на колонну",
                "responsible": "Инженер ННБ",
                "critical": True,
                "conditions": []
            },
            {
                "id": "3",
                "title": "Проверка содержания песка",
                "action": "Измерить содержание песка в растворе",
                "responsible": "Лаборант",
                "critical": False,
                "conditions": [
                    {"type": "sand_limit", "action": "Если песок > лимита Заказчика → добавить шаг согласования"}
                ]
            },
            {
                "id": "4",
                "title": "Подготовка технологической пачки",
                "action": "Приготовить пачку с ЛЦМ согласно рецептуре",
                "responsible": "Инженер по растворам",
                "critical": True,
                "conditions": []
            },
            {
                "id": "5",
                "title": "Прокачка пачки в интервал прихвата",
                "action": "Прокачать пачку с контролем давления и объема",
                "responsible": "Бурильщик",
                "critical": True,
                "conditions": []
            },
            {
                "id": "6",
                "title": "Активация ясса (если есть)",
                "action": "Взвести и активировать буровой ясс согласно регламенту",
                "responsible": "Инженер ННБ",
                "critical": True,
                "conditions": []
            },
            {
                "id": "7",
                "title": "Контроль освобождения",
                "action": "Контролировать вес и давление при попытках освобождения",
                "responsible": "Инженер ННБ",
                "critical": True,
                "conditions": []
            },
            {
                "id": "8",
                "title": "Документирование",
                "action": "Зафиксировать все параметры и результаты в рапорте",
                "responsible": "Инженер ННБ",
                "critical": False,
                "conditions": []
            }
        ],
        "critical_alerts": [
            "ЗАПРЕЩЕНО: Превышение допустимой нагрузки на колонну",
            "ЗАПРЕЩЕНО: Продолжение работ без восстановления уровня раствора",
            "ОБЯЗАТЕЛЬНО: Уведомление Заказчика при критическом прихвате"
        ]
    },
    
    "Контроль интенсивности искривления (DLS)": {
        "description": "Алгоритм контроля и коррекции интенсивности искривления ствола",
        "standard": "СТО ИНТИ S.QS.7, API RP 7G",
        "steps": [
            {
                "id": "1",
                "title": "Замер инклинометрии",
                "action": "Снять показания MWD/LWD на текущей глубине",
                "responsible": "Инженер MWD",
                "critical": False,
                "conditions": []
            },
            {
                "id": "2",
                "title": "Расчет фактического DLS",
                "action": "Рассчитать интенсивность искривления по последним 3 замерам",
                "responsible": "Инженер ННБ",
                "critical": True,
                "conditions": []
            },
            {
                "id": "3",
                "title": "Сравнение с проектом",
                "action": "Сверить фактический DLS с проектным профилем",
                "responsible": "Инженер ННБ",
                "critical": True,
                "conditions": [
                    {"type": "dls_limit", "action": "Если DLS > 3 град/10м → корректировка режима"}
                ]
            },
            {
                "id": "4",
                "title": "Проверка КНБК",
                "action": "Оценить состояние калибраторов и центраторов",
                "responsible": "Инженер ННБ",
                "critical": False,
                "conditions": []
            },
            {
                "id": "5",
                "title": "Корректировка режима (если нужно)",
                "action": "Снизить WOB на 20-30%, скорректировать RPM",
                "responsible": "Бурильщик",
                "critical": True,
                "conditions": [
                    {"type": "dls_exceeded", "action": "Обязательный шаг при превышении DLS"}
                ]
            },
            {
                "id": "6",
                "title": "Контроль после корректировки",
                "action": "Продолжить бурение с контролем DLS каждые 10-15 м",
                "responsible": "Инженер ННБ",
                "critical": True,
                "conditions": []
            }
        ],
        "critical_alerts": [
            "ВНИМАНИЕ: DLS > 4 град/10м — риск ключевых посадок",
            "ОБЯЗАТЕЛЬНО: Корректировка режима при превышении проектного DLS"
        ]
    },
    
    "Предотвращение поглощений бурового раствора": {
        "description": "Алгоритм контроля и предотвращения поглощений",
        "standard": "СТО ИНТИ S.100.3",
        "steps": [
            {
                "id": "1",
                "title": "Контроль уровня раствора",
                "action": "Проверять уровень в приемной емкости каждые 15 минут",
                "responsible": "Бурильщик",
                "critical": True,
                "conditions": []
            },
            {
                "id": "2",
                "title": "Анализ тренда",
                "action": "Оценить динамику уровня (стабильный/снижение/рост)",
                "responsible": "Инженер по растворам",
                "critical": True,
                "conditions": [
                    {"type": "level_drop", "action": "Если уровень падает → переход к шагу 3"}
                ]
            },
            {
                "id": "3",
                "title": "Подготовка ЛЦМ",
                "action": "Приготовить порцию материала для ликвидации поглощений",
                "responsible": "Инженер по растворам",
                "critical": True,
                "conditions": []
            },
            {
                "id": "4",
                "title": "Снижение плотности (если возможно)",
                "action": "Снизить плотность раствора в пределах допуска",
                "responsible": "Инженер по растворам",
                "critical": False,
                "conditions": [
                    {"type": "density_check", "action": "Проверить через Compliance Engine минимальную плотность"}
                ]
            },
            {
                "id": "5",
                "title": "Прокачка ЛЦМ",
                "action": "Прокачать порцию ЛЦМ в интервал поглощения",
                "responsible": "Бурильщик",
                "critical": True,
                "conditions": []
            },
            {
                "id": "6",
                "title": "Контроль восстановления",
                "action": "Мониторить уровень и давление после прокачки",
                "responsible": "Бурильщик",
                "critical": True,
                "conditions": []
            }
        ],
        "critical_alerts": [
            "ЗАПРЕЩЕНО: Продолжение бурения при падении уровня раствора",
            "ОБЯЗАТЕЛЬНО: Уведомление Заказчика при интенсивном поглощении"
        ]
    }
}


# ============================================================================
# ГЕНЕРАТОР БЛОК-СХЕМ
# ============================================================================

class FlowchartGenerator:
    """Генератор персонализированных блок-схем на основе требований ЛНД"""
    
    def __init__(self, operation_name: str, client_name: str, current_params: Dict):
        self.operation = OPERATIONAL_KB.get(operation_name)
        self.client = client_name
        self.params = current_params
        self.alerts = []
        
    def analyze_conditions(self) -> List[Dict]:
        """Анализирует текущие параметры и определяет дополнительные шаги"""
        additional_steps = []
        
        if not self.operation:
            return additional_steps
        
        for step in self.operation["steps"]:
            for condition in step.get("conditions", []):
                # Проверка лимита песка
                if condition["type"] == "sand_limit":
                    sand_limit, _, source = compliance.get_limit(
                        self.client, 'sand_limit', 'max_sand_content', 0.5
                    )
                    actual_sand = self.params.get('sand_content', 0.0)
                    
                    if actual_sand > sand_limit:
                        self.alerts.append({
                            "type": "warning",
                            "message": f"Превышен лимит песка по {self.client}: {actual_sand:.2f}% > {sand_limit:.2f}% ({source})",
                            "action": "Добавить шаг согласования с Заказчиком"
                        })
                        additional_steps.append({
                            "id": f"{step['id']}.1",
                            "title": "Согласование с Заказчиком",
                            "action": f"Получить разрешение от супервайзера {self.client} на продолжение работ при повышенном песке",
                            "responsible": "Инженер ННБ",
                            "critical": True,
                            "insert_after": step["id"]
                        })
                
                # Проверка DLS
                elif condition["type"] == "dls_limit":
                    actual_dls = self.params.get('dls', 0.0)
                    if actual_dls > 3.0:
                        self.alerts.append({
                            "type": "critical",
                            "message": f"Превышен DLS: {actual_dls:.1f} град/10м > 3.0 град/10м",
                            "action": "Обязательная корректировка режима бурения"
                        })
        
        return additional_steps
    
    def generate_flowchart_data(self) -> Dict:
        """Генерирует данные для визуализации блок-схемы"""
        if not self.operation:
            return {"nodes": [], "edges": [], "alerts": []}
        
        # Анализируем условия
        additional_steps = self.analyze_conditions()
        
        # Формируем узлы
        nodes = []
        edges = []
        
        # Стартовый узел
        nodes.append({
            "id": "start",
            "label": f"Начало: {self.operation['description'][:50]}",
            "type": "start",
            "x": 0, "y": 0
        })
        
        # Основные шаги
        all_steps = self.operation["steps"] + additional_steps
        all_steps.sort(key=lambda x: x["id"])
        
        for idx, step in enumerate(all_steps):
            nodes.append({
                "id": step["id"],
                "label": f"{step['id']}. {step['title']}",
                "type": "critical" if step.get("critical") else "normal",
                "x": 0,
                "y": (idx + 1) * 100
            })
            
            # Связь с предыдущим узлом
            if idx == 0:
                edges.append({"from": "start", "to": step["id"]})
            else:
                prev_id = all_steps[idx - 1]["id"]
                edges.append({"from": prev_id, "to": step["id"]})
        
        # Финальный узел
        nodes.append({
            "id": "end",
            "label": "Завершение операции",
            "type": "end",
            "x": 0,
            "y": (len(all_steps) + 1) * 100
        })
        edges.append({"from": all_steps[-1]["id"], "to": "end"})
        
        return {
            "nodes": nodes,
            "edges": edges,
            "alerts": self.alerts,
            "operation": self.operation["description"],
            "standard": self.operation["standard"]
        }


# ============================================================================
# ИНТЕРФЕЙСНЫЕ КОМПОНЕНТЫ
# ============================================================================

def create_compliance_layout():
    """Основной макет модуля комплаенса"""
    return html.Div([
        # Заголовок
        html.Div([
            html.H2("Интеллектуальный генератор алгоритмов действий", style={"color": "white", "margin": "0"}),
            html.P("Анализ требований ЛНД и генерация персонализированных блок-схем", 
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "20px", "borderRadius": "8px", "marginBottom": "20px"}),
        
        # Панель параметров
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Технологическая операция:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Dropdown(
                            id='comp-operation-select',
                            options=[{"label": op, "value": op} for op in OPERATIONAL_KB.keys()],
                            value=list(OPERATIONAL_KB.keys())[0],
                            clearable=False,
                            style={"width": "100%"}
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Заказчик:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Dropdown(
                            id='comp-client-select',
                            options=[{"label": c, "value": c} for c in ["Роснефть", "Газпром нефть", "ЛУКОЙЛ", "Татнефть", "Прочие"]],
                            value="Роснефть",
                            clearable=False,
                            style={"width": "100%"}
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Содержание песка, %:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Input(
                            id='comp-sand-input',
                            type='number',
                            value=0.5,
                            min=0.0,
                            max=10.0,
                            step=0.1,
                            style={"width": "100%", "padding": "8px"}
                        )
                    ], width=2),
                    dbc.Col([
                        html.Label("DLS, град/10м:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Input(
                            id='comp-dls-input',
                            type='number',
                            value=1.5,
                            min=0.0,
                            max=10.0,
                            step=0.1,
                            style={"width": "100%", "padding": "8px"}
                        )
                    ], width=2),
                ], className="mb-3"),
            ])
        ], className="mb-4"),
        
        # Алерты
        html.Div(id='compliance-alerts', style={"marginBottom": "20px"}),
        
        # Визуализация блок-схемы
        html.H4("Алгоритм действий", style={"color": "#0F172A", "marginBottom": "10px"}),
        dcc.Graph(id='flowchart-visualization', style={"height": "800px"}),
        
        # Детализация шагов
        html.Div(id='flowchart-details', style={"marginTop": "20px"}),
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def compliance_checklist_callbacks(app, data_bridge):
    
    @app.callback(
        [Output('flowchart-visualization', 'figure'),
         Output('compliance-alerts', 'children'),
         Output('flowchart-details', 'children')],
        [Input('comp-operation-select', 'value'),
         Input('comp-client-select', 'value'),
         Input('comp-sand-input', 'value'),
         Input('comp-dls-input', 'value')]
    )
    def update_flowchart(operation, client, sand_content, dls):
        if not operation or operation not in OPERATIONAL_KB:
            return go.Figure(), html.Div(), html.Div()
        
        # Текущие параметры
        current_params = {
            'sand_content': sand_content if sand_content else 0.0,
            'dls': dls if dls else 0.0
        }
        
        # Генерация блок-схемы
        generator = FlowchartGenerator(operation, client, current_params)
        flowchart_data = generator.generate_flowchart_data()
        
        # Визуализация через Plotly
        fig = go.Figure()
        
        nodes = flowchart_data["nodes"]
        edges = flowchart_data["edges"]
        
        # Рисуем связи
        for edge in edges:
            from_node = next((n for n in nodes if n["id"] == edge["from"]), None)
            to_node = next((n for n in nodes if n["id"] == edge["to"]), None)
            
            if from_node and to_node:
                fig.add_trace(go.Scatter(
                    x=[from_node["x"], to_node["x"]],
                    y=[from_node["y"], to_node["y"]],
                    mode='lines',
                    line=dict(color='#64748B', width=2),
                    showlegend=False,
                    hoverinfo='skip'
                ))
        
        # Рисуем узлы
        for node in nodes:
            color = '#10B981' if node["type"] == "start" else ('#EF4444' if node["type"] == "critical" else ('#3B82F6' if node["type"] == "end" else '#64748B'))
            size = 20 if node["type"] in ["start", "end"] else 15
            
            fig.add_trace(go.Scatter(
                x=[node["x"]],
                y=[node["y"]],
                mode='markers+text',
                marker=dict(size=size, color=color, line=dict(width=2, color='white')),
                text=[node["label"]],
                textposition='middle right',
                textfont=dict(size=11, color='#0F172A'),
                showlegend=False,
                hoverinfo='text',
                hovertext=node["label"]
            ))
        
        fig.update_layout(
            title=f"Алгоритм: {flowchart_data['operation']}",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-50, 400]),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange='reversed'),
            template='plotly_white',
            height=800,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        # Алерты
        alerts_html = []
        for alert in flowchart_data["alerts"]:
            color = "#EF4444" if alert["type"] == "critical" else "#F59E0B"
            alerts_html.append(html.Div(
                f"⚠️ {alert['message']}",
                style={"color": color, "fontWeight": "bold", "padding": "10px", "backgroundColor": color + "20", 
                       "borderRadius": "6px", "marginBottom": "10px", "border": f"1px solid {color}"}
            ))
        
        if not alerts_html:
            alerts_html.append(html.Div(
                "✅ Все параметры в норме. Стандартный алгоритм применяется без изменений.",
                style={"color": "#10B981", "fontWeight": "bold", "padding": "10px", "backgroundColor": "#10B98120",
                       "borderRadius": "6px", "border": "1px solid #10B981"}
            ))
        
        # Детализация шагов
        details_html = []
        for node in nodes:
            if node["type"] not in ["start", "end"]:
                step_data = next((s for s in OPERATIONAL_KB[operation]["steps"] if s["id"] == node["id"]), None)
                if step_data:
                    details_html.append(html.Div([
                        html.H6(f"Шаг {node['id']}: {step_data['title']}", 
                               style={"color": "#EF4444" if step_data.get("critical") else "#0F172A", "marginBottom": "5px"}),
                        html.P(step_data["action"], style={"margin": "5px 0", "fontSize": "13px"}),
                        html.Small(f"Ответственный: {step_data['responsible']}", style={"color": "#64748B"})
                    ], style={"padding": "10px", "backgroundColor": "#F8FAFC", "borderRadius": "6px", "marginBottom": "10px"}))
        
        return fig, html.Div(alerts_html), html.Div(details_html)
