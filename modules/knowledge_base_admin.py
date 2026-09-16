"""
МОДУЛЬ УПРАВЛЕНИЯ БАЗОЙ ЗНАНИЙ (АДМИНИСТРАТИВНЫЙ)
Интерфейс для инженера по НТД:
- Просмотр и редактирование правил комплаенса
- Реестр договоров и технических заданий (ТЗ)
- Запуск локального ИИ-парсера документов
- Загрузка обновлений от парсера
- Управление версиями и историей изменений
- Экспорт пакетов для синхронизации с буровыми
- Валидация целостности данных
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import dash_table

from utils.compliance_engine import get_compliance_engine

compliance = get_compliance_engine()


# ============================================================================
# ИНТЕРФЕЙСНЫЕ КОМПОНЕНТЫ
# ============================================================================

def create_kb_admin_layout():
    """Основной макет модуля управления базой знаний"""
    return html.Div([
        # Заголовок
        html.Div([
            html.H2("Управление базой знаний", style={"color": "white", "margin": "0"}),
            html.P("Административный интерфейс для инженера по НТД", 
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "20px", "borderRadius": "8px", "marginBottom": "20px"}),
        
        # Статистика базы знаний
        html.Div(id='kb-stats-cards', className="mb-4"),
        
        # Вкладки управления
        dcc.Tabs(id='kb-admin-tabs', value='tab-rules', className='custom-tabs', children=[
            dcc.Tab(label='Правила комплаенса', value='tab-rules'),
            dcc.Tab(label='Договоры и ТЗ', value='tab-contracts'),
            dcc.Tab(label='Загрузка обновлений', value='tab-uploads'),
            dcc.Tab(label='История изменений', value='tab-history'),
            dcc.Tab(label='Экспорт для буровых', value='tab-export'),
            dcc.Tab(label='Валидация данных', value='tab-validation'),
        ]),
        
        html.Div(id='kb-admin-tabs-content', style={"marginTop": "20px"}),
    ])


def create_rules_tab():
    """Вкладка: Управление правилами комплаенса"""
    return html.Div([
        html.H4("Правила комплаенса (ЛНД, ТК, СТО)", style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Row([
            dbc.Col([
                html.Label("Категория:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Dropdown(
                    id='kb-filter-category',
                    options=[
                        {"label": "Все категории", "value": "all"},
                        {"label": "Лимит DLS", "value": "dls_limit"},
                        {"label": "Лимит песка", "value": "sand_limit"},
                        {"label": "Буфер ЭЦП", "value": "ecd_buffer"},
                        {"label": "МПИ ВЗД", "value": "mpi_hours"},
                    ],
                    value="all", clearable=False
                )
            ], width=3),
            dbc.Col([
                html.Label("Заказчик:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Dropdown(
                    id='kb-filter-client',
                    options=[
                        {"label": "Все заказчики", "value": "all"},
                        {"label": "Роснефть", "value": "Роснефть"},
                        {"label": "Газпром нефть", "value": "Газпром нефть"},
                        {"label": "ЛУКОЙЛ", "value": "ЛУКОЙЛ"},
                        {"label": "Татнефть", "value": "Татнефть"},
                        {"label": "Прочие", "value": "Прочие"},
                    ],
                    value="all", clearable=False
                )
            ], width=3),
            dbc.Col([
                html.Label("Поиск:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Input(id='kb-search-rules', type='text', placeholder="Поиск по описанию...", style={"width": "100%", "padding": "8px"})
            ], width=4),
            dbc.Col([
                html.Div(style={"marginTop": "25px"}),
                dbc.Button("Добавить правило", id='btn-add-rule', color="primary", className="w-100")
            ], width=2),
        ], className="mb-3"),
        
        html.Div(id='kb-rules-table-container'),
        
        dbc.Modal([
            dbc.ModalHeader("Добавить/Редактировать правило"),
            dbc.ModalBody([
                dbc.Form([
                    dbc.Row([
                        dbc.Col([dbc.Label("ID правила"), dbc.Input(id='rule-id-input', type='text', placeholder="Например: TAT_dls_limit")], width=6),
                        dbc.Col([dbc.Label("Категория"), dbc.Select(id='rule-category-input', options=[
                            {"label": "Лимит DLS", "value": "dls_limit"}, {"label": "Лимит песка", "value": "sand_limit"},
                            {"label": "Буфер ЭЦП", "value": "ecd_buffer"}, {"label": "МПИ ВЗД", "value": "mpi_hours"},
                        ])], width=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([dbc.Label("Параметр"), dbc.Input(id='rule-parameter-input', type='text', placeholder="max_dls")], width=6),
                        dbc.Col([dbc.Label("Значение"), dbc.Input(id='rule-value-input', type='number', step=0.01)], width=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([dbc.Label("Единица измерения"), dbc.Input(id='rule-unit-input', type='text', placeholder="°/10м")], width=6),
                        dbc.Col([dbc.Label("Заказчик"), dbc.Input(id='rule-client-input', type='text', placeholder="Татнефть")], width=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([dbc.Label("Источник стандарта"), dbc.Input(id='rule-source-input', type='text', placeholder="ТЗ №123 от 01.01.2024")], width=12),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([dbc.Label("Описание"), dbc.Textarea(id='rule-description-input', rows=3)], width=12),
                    ], className="mb-3"),
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Отмена", id='btn-cancel-rule', className="ms-auto", color="secondary"),
                dbc.Button("Сохранить", id='btn-save-rule', color="primary"),
            ]),
        ], id='rule-modal', size="lg", is_open=False),
    ])


def create_contracts_tab():
    """Вкладка: Реестр договоров и технических заданий"""
    return html.Div([
        html.H4("Реестр договоров и технических заданий", style={"color": "#0F172A", "marginBottom": "15px"}),
        html.P("Загружайте сюда структурированные выгрузки лимитов из ТЗ (Excel) или JSON от локального ИИ-парсера.", 
              style={"color": "#64748B", "marginBottom": "15px"}),
        
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Заказчик (Холдинг/ДОР):", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Input(id='contract-client-input', type='text', placeholder="Например: Татнефть", 
                                 style={"width": "100%", "padding": "8px", "marginBottom": "10px"})
                    ], width=4),
                    dbc.Col([
                        html.Label("Номер/Название договора:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Input(id='contract-name-input', type='text', placeholder="ТЗ-2024-001", 
                                 style={"width": "100%", "padding": "8px", "marginBottom": "10px"})
                    ], width=4),
                    dbc.Col([
                        html.Label("Дата вступления в силу:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Input(id='contract-date-input', type='date', 
                                 style={"width": "100%", "padding": "8px", "marginBottom": "10px"})
                    ], width=4),
                ], className="mb-3"),
                
                dcc.Upload(
                    id='upload-contract-file',
                    children=html.Div([
                        'Перетащите файл с лимитами (.xlsx или .json) сюда или ',
                        html.A('выберите файл', style={"color": "#2563eb", "fontWeight": "bold"})
                    ]),
                    style={
                        'width': '100%', 'height': '80px', 'lineHeight': '80px',
                        'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '8px',
                        'textAlign': 'center', 'backgroundColor': '#F8FAFC', 'marginBottom': '15px'
                    },
                    multiple=False
                ),
                
                dbc.Button("Применить лимиты из документа", id='btn-apply-contract', color="success", className="w-100"),
                html.Div(id='contract-upload-status', style={"marginTop": "15px"}),
            ])
        ], className="mb-4"),
        
        html.H5("Активные договоры в системе:", style={"color": "#0F172A", "marginBottom": "10px"}),
        dash_table.DataTable(
            columns=[
                {"name": "Заказчик", "id": "client"},
                {"name": "Договор/ТЗ", "id": "name"},
                {"name": "Дата", "id": "date"},
                {"name": "Статус", "id": "status"}
            ],
            data=[
                {"client": "Роснефть", "name": "ТЗ-2023-105", "date": "2023-01-01", "status": "Активен"},
                {"client": "Татнефть", "name": "Доп. соглашение №4", "date": "2024-03-01", "status": "Активен"},
                {"client": "Газпром нефть", "name": "СТ ГПН-2024", "date": "2024-01-15", "status": "Активен"},
            ],
            style_table={'overflowX': 'auto', 'border': '1px solid #E2E8F0', 'borderRadius': '8px'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '13px'},
            style_header={'backgroundColor': '#F1F5F9', 'fontWeight': 'bold'}
        )
    ])


def create_uploads_tab():
    """Вкладка: Загрузка обновлений + запуск парсера"""
    return html.Div([
        html.H4("Загрузка обновлений базы знаний", style={"color": "#0F172A", "marginBottom": "15px"}),
        
        # БЛОК 1: Запуск локального ИИ-парсера
        dbc.Card([
            dbc.CardHeader(html.H5("🤖 Локальный ИИ-парсер документов", style={"margin": "0"})),
            dbc.CardBody([
                html.P("Автоматическое извлечение лимитов из PDF-документов (ТЗ, договоры) с помощью локального ИИ (Ollama + Qwen2.5).",
                      style={"color": "#64748B", "marginBottom": "15px"}),
                
                html.Div([
                    html.H6("Инструкция:", style={"marginBottom": "10px"}),
                    html.Ol([
                        html.Li("Положите PDF-файлы в папку: ", style={"marginBottom": "5px"}),
                        html.Code("data/input_docs/", style={"backgroundColor": "#F1F5F9", "padding": "2px 6px", "borderRadius": "4px"}),
                        html.Li("Нажмите кнопку ниже для запуска парсера", style={"marginBottom": "5px"}),
                        html.Li("Дождитесь завершения обработки (30-60 сек на документ)", style={"marginBottom": "5px"}),
                        html.Li("Результат будет автоматически загружен в базу знаний", style={"marginBottom": "5px"}),
                    ], style={"fontSize": "13px", "paddingLeft": "20px"})
                ], style={"backgroundColor": "#F8FAFC", "padding": "15px", "borderRadius": "6px", "marginBottom": "15px"}),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Button(" Запустить парсер", id='btn-run-parser', color="primary", className="w-100", size="lg"),
                    ], width=6),
                    dbc.Col([
                        dbc.Button(" Открыть папку input_docs", id='btn-open-folder', color="secondary", className="w-100", size="lg"),
                    ], width=6),
                ], className="mb-3"),
                
                html.Div(id='parser-status', style={"marginTop": "15px"}),
                
                # Лог обработки
                html.Div(id='parser-log', style={
                    "backgroundColor": "#1E293B", "color": "#10B981", "padding": "15px",
                    "borderRadius": "6px", "fontFamily": "monospace", "fontSize": "12px",
                    "maxHeight": "300px", "overflowY": "auto", "display": "none"
                }),
            ])
        ], className="mb-4"),
        
        # БЛОК 2: Ручная загрузка JSON
        dbc.Card([
            dbc.CardHeader(html.H5(" Ручная загрузка JSON от парсера", style={"margin": "0"})),
            dbc.CardBody([
                html.P("Если вы обработали документы на другом компьютере, загрузите готовый JSON-файл здесь.",
                      style={"color": "#64748B", "marginBottom": "15px"}),
                
                dcc.Upload(
                    id='upload-kb-update',
                    children=html.Div([
                        'Перетащите файл kb_update_*.json сюда или ',
                        html.A('выберите файл', style={"color": "#2563eb", "fontWeight": "bold"})
                    ]),
                    style={
                        'width': '100%', 'height': '100px', 'lineHeight': '100px',
                        'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '8px',
                        'textAlign': 'center', 'backgroundColor': '#F8FAFC', 'marginBottom': '15px'
                    },
                    multiple=False
                ),
                
                dbc.Button("Обработать и применить", id='btn-process-upload', color="success", className="w-100"),
                html.Div(id='upload-status', style={"marginTop": "15px"}),
            ])
        ], className="mb-4"),
    ])


def create_history_tab():
    """Вкладка: История изменений"""
    return html.Div([
        html.H4("История изменений базы знаний", style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Row([
            dbc.Col([
                html.Label("Период:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.DatePickerRange(
                    id='kb-history-date-range',
                    start_date=datetime.now().replace(day=1),
                    end_date=datetime.now(),
                    style={"width": "100%"}
                )
            ], width=6),
            dbc.Col([
                html.Div(style={"marginTop": "25px"}),
                dbc.Button("Показать историю", id='btn-show-history', color="primary", className="w-100")
            ], width=3),
            dbc.Col([
                html.Div(style={"marginTop": "25px"}),
                dbc.Button("Экспорт истории", id='btn-export-history', color="secondary", className="w-100")
            ], width=3),
        ], className="mb-3"),
        
        html.Div(id='kb-history-table', children=html.P("История изменений будет отображена здесь.", className="text-muted")),
    ])


def create_export_tab():
    """Вкладка: Экспорт для буровых"""
    return html.Div([
        html.H4("Экспорт пакетов обновлений для буровых", style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Card([
            dbc.CardBody([
                html.H5("Формирование пакета синхронизации", style={"marginBottom": "15px"}),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Версия пакета:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dcc.Input(id='export-version', type='text', value=datetime.now().strftime("%Y.%m.%d"), style={"width": "100%", "padding": "8px"})
                    ], width=4),
                    dbc.Col([
                        html.Label("Включить данные:", style={"fontWeight": "bold", "fontSize": "13px"}),
                        dbc.Checklist(
                            id='export-include-rules',
                            options=[
                                {"label": " Все правила комплаенса", "value": "rules"},
                                {"label": " Операционные алгоритмы", "value": "operations"},
                            ],
                            value=["rules", "operations"],
                            inline=True
                        )
                    ], width=8),
                ], className="mb-3"),
                
                dbc.Button("Сформировать пакет", id='btn-generate-package', color="primary", className="w-100 mb-3"),
                
                html.Div(id='export-status'),
                dcc.Download(id="download-kb-package"),
            ])
        ]),
    ])


def create_validation_tab():
    """Вкладка: Валидация данных"""
    return html.Div([
        html.H4("Валидация целостности базы знаний", style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Button("Запустить проверку", id='btn-run-validation', color="primary", className="w-100 mb-3"),
        html.Div(id='validation-results'),
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def kb_admin_callbacks(app, data_bridge):
    
    # 1. Переключение вкладок
    @app.callback(
        Output('kb-admin-tabs-content', 'children'),
        Input('kb-admin-tabs', 'value')
    )
    def render_kb_tab(tab_value):
        if tab_value == 'tab-rules': return create_rules_tab()
        elif tab_value == 'tab-contracts': return create_contracts_tab()
        elif tab_value == 'tab-uploads': return create_uploads_tab()
        elif tab_value == 'tab-history': return create_history_tab()
        elif tab_value == 'tab-export': return create_export_tab()
        elif tab_value == 'tab-validation': return create_validation_tab()
        return html.Div("Выберите вкладку")
    
    # 2. Статистика базы знаний
    @app.callback(
        Output('kb-stats-cards', 'children'),
        Input('kb-admin-tabs', 'value')
    )
    def update_kb_stats(_):
        rules_count = len(compliance.rules_cache)
        clients_count = len(set(r.client_hierarchy for r in compliance.rules_cache.values() if r.client_hierarchy != '*'))
        categories_count = len(set(r.category for r in compliance.rules_cache.values()))
        
        return dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div("Всего правил", style={"fontSize": "12px", "color": "#64748B"}),
                    html.Div(f"{rules_count}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0F172A"})
                ], style={"backgroundColor": "#F1F5F9", "padding": "15px", "borderRadius": "6px", "textAlign": "center"})
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Div("Заказчиков", style={"fontSize": "12px", "color": "#64748B"}),
                    html.Div(f"{clients_count}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0F172A"})
                ], style={"backgroundColor": "#F1F5F9", "padding": "15px", "borderRadius": "6px", "textAlign": "center"})
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Div("Категорий", style={"fontSize": "12px", "color": "#64748B"}),
                    html.Div(f"{categories_count}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0F172A"})
                ], style={"backgroundColor": "#F1F5F9", "padding": "15px", "borderRadius": "6px", "textAlign": "center"})
            ], width=4),
        ])
    
    # 3. Таблица правил с фильтрацией
    @app.callback(
        Output('kb-rules-table-container', 'children'),
        [Input('kb-filter-category', 'value'),
         Input('kb-filter-client', 'value'),
         Input('kb-search-rules', 'value')]
    )
    def update_rules_table(category, client, search):
        rules = []
        for rule in compliance.rules_cache.values():
            if category != 'all' and rule.category != category:
                continue
            if client != 'all' and rule.client_hierarchy != client:
                continue
            if search and search.lower() not in rule.description.lower():
                continue
            
            rules.append({
                'ID': rule.rule_id,
                'Категория': rule.category,
                'Параметр': rule.parameter,
                'Значение': f"{rule.value} {rule.unit}",
                'Заказчик': rule.client_hierarchy,
                'Источник': rule.standard_source,
                'Приоритет': rule.priority,
                'Описание': rule.description[:50] + '...' if len(rule.description) > 50 else rule.description
            })
        
        if not rules:
            return html.Div("Нет правил, соответствующих фильтрам.", style={"color": "#64748B", "fontStyle": "italic"})
        
        df = pd.DataFrame(rules)
        
        return dash_table.DataTable(
            id='kb-rules-table',
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            style_table={'overflowX': 'auto', 'border': '1px solid #E2E8F0', 'borderRadius': '8px'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '12px'},
            style_header={'backgroundColor': '#F1F5F9', 'fontWeight': 'bold'},
            page_size=20,
            sort_action='native',
            filter_action='native'
        )
    
    # 4. Модальное окно добавления правила
    @app.callback(
        Output('rule-modal', 'is_open'),
        [Input('btn-add-rule', 'n_clicks'),
         Input('btn-cancel-rule', 'n_clicks'),
         Input('btn-save-rule', 'n_clicks')],
        State('rule-modal', 'is_open')
    )
    def toggle_modal(add_clicks, cancel_clicks, save_clicks, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return False
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'btn-add-rule':
            return True
        elif button_id in ['btn-cancel-rule', 'btn-save-rule']:
            return False
        
        return is_open
    
    # 5. Сохранение нового правила
    @app.callback(
        Output('upload-status', 'children', allow_duplicate=True),
        Input('btn-save-rule', 'n_clicks'),
        [State('rule-id-input', 'value'),
         State('rule-category-input', 'value'),
         State('rule-parameter-input', 'value'),
         State('rule-value-input', 'value'),
         State('rule-unit-input', 'value'),
         State('rule-client-input', 'value'),
         State('rule-source-input', 'value'),
         State('rule-description-input', 'value')],
        prevent_initial_call=True
    )
    def save_new_rule(n_clicks, rule_id, category, parameter, value, unit, client, source, description):
        if not all([rule_id, category, parameter, value, unit, client]):
            return html.Div("Заполните все обязательные поля!", style={"color": "#EF4444"})
        
        from utils.compliance_engine import ComplianceRule
        
        new_rule = ComplianceRule(
            rule_id=rule_id,
            category=category,
            parameter=parameter,
            value=float(value),
            unit=unit,
            standard_source=source or "Ручное добавление",
            priority=3,
            client_hierarchy=client,
            description=description or "",
            mandatory=True,
            effective_date=datetime.now().strftime("%Y-%m-%d")
        )
        
        compliance.rules_cache[rule_id] = new_rule
        compliance.save_rules()
        
        return html.Div(f"✅ Правило {rule_id} успешно добавлено!", style={"color": "#10B981", "fontWeight": "bold"})
    
    # 6. ЗАПУСК ЛОКАЛЬНОГО ИИ-ПАРСЕРА
    @app.callback(
        [Output('parser-status', 'children'),
         Output('parser-log', 'children'),
         Output('parser-log', 'style')],
        Input('btn-run-parser', 'n_clicks'),
        prevent_initial_call=True
    )
    def run_local_parser(n_clicks):
        if not n_clicks:
            return html.Div(), "", {"display": "none"}
        
        # Проверяем наличие папки input_docs
        project_root = Path(__file__).parent.parent
        input_dir = project_root / "data" / "input_docs"
        
        if not input_dir.exists():
            input_dir.mkdir(parents=True, exist_ok=True)
            return (
                dbc.Alert("📁 Папка input_docs создана. Положите туда PDF-файлы и запустите парсер снова.", color="warning"),
                "",
                {"display": "block"}
            )
        
        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            return (
                dbc.Alert(f"⚠️ Папка input_docs пуста. Положите PDF-файлы в: {input_dir}", color="warning"),
                "",
                {"display": "block"}
            )
        
        # Запускаем парсер через subprocess
        parser_script = project_root / "tools" / "local_ai_parser.py"
        
        if not parser_script.exists():
            return (
                dbc.Alert("❌ Скрипт парсера не найден: tools/local_ai_parser.py", color="danger"),
                "",
                {"display": "block"}
            )
        
        try:
            # Запуск парсера
            result = subprocess.run(
                [sys.executable, str(parser_script), "--folder", str(input_dir)],
                capture_output=True,
                text=True,
                timeout=600  # 10 минут максимум
            )
            
            # Формируем лог
            log_text = f"=== ЗАПУСК ПАРСЕРА ===\n"
            log_text += f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            log_text += f"PDF файлов: {len(pdf_files)}\n\n"
            log_text += result.stdout
            if result.stderr:
                log_text += f"\n=== ОШИБКИ ===\n{result.stderr}"
            
            # Проверяем результат
            if result.returncode == 0:
                # Парсер отработал успешно, теперь загружаем результат
                output_file = project_root / "data" / "kb_update.json"
                
                if output_file.exists():
                    with open(output_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    rules_added = 0
                    for rule_data in data.get('rules', []):
                        from utils.compliance_engine import ComplianceRule
                        try:
                            rule = ComplianceRule(**rule_data)
                            compliance.rules_cache[rule.rule_id] = rule
                            rules_added += 1
                        except Exception as e:
                            log_text += f"\n⚠️ Ошибка добавления правила {rule_data.get('rule_id', 'unknown')}: {e}"
                    
                    compliance.save_rules()
                    
                    status = dbc.Alert(
                        f"✅ Парсер завершил работу! Загружено {rules_added} правил из {len(pdf_files)} документов.",
                        color="success"
                    )
                else:
                    status = dbc.Alert("⚠️ Парсер отработал, но файл kb_update.json не создан.", color="warning")
            else:
                status = dbc.Alert(f"❌ Ошибка парсера (код {result.returncode}). Проверьте лог ниже.", color="danger")
            
            return status, log_text.replace('\n', '<br>'), {"display": "block"}
        
        except subprocess.TimeoutExpired:
            return (
                dbc.Alert("⏱️ Парсер не завершился за 10 минут. Возможно, Ollama недоступна.", color="danger"),
                "Таймаут выполнения",
                {"display": "block"}
            )
        except Exception as e:
            return (
                dbc.Alert(f"❌ Критическая ошибка: {str(e)}", color="danger"),
                str(e),
                {"display": "block"}
            )
    
    # 7. Открыть папку input_docs
    @app.callback(
        Output('parser-status', 'children', allow_duplicate=True),
        Input('btn-open-folder', 'n_clicks'),
        prevent_initial_call=True
    )
    def open_input_folder(n_clicks):
        if not n_clicks:
            return html.Div()
        
        import platform
        project_root = Path(__file__).parent.parent
        input_dir = project_root / "data" / "input_docs"
        input_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if platform.system() == 'Windows':
                import os
                os.startfile(str(input_dir))
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', str(input_dir)])
            else:
                subprocess.Popen(['xdg-open', str(input_dir)])
            
            return dbc.Alert(f"📁 Папка открыта: {input_dir}", color="info")
        except Exception as e:
            return dbc.Alert(f"⚠️ Не удалось открыть папку: {e}", color="warning")
    
    # 8. Загрузка обновлений от ИИ-парсера (ручная)
    @app.callback(
        Output('upload-status', 'children'),
        Input('btn-process-upload', 'n_clicks'),
        State('upload-kb-update', 'contents'),
        State('upload-kb-update', 'filename'),
        prevent_initial_call=True
    )
    def process_upload(n_clicks, contents, filename):
        if contents is None:
            return html.Div("Сначала выберите файл для загрузки.", style={"color": "#F59E0B"})
        
        import base64
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        try:
            data = json.loads(decoded)
            
            if 'rules' not in data:
                return html.Div("Неверный формат файла. Ожидается JSON с ключом 'rules'.", style={"color": "#EF4444"})
            
            rules_added = 0
            for rule_data in data['rules']:
                from utils.compliance_engine import ComplianceRule
                rule = ComplianceRule(**rule_data)
                compliance.rules_cache[rule.rule_id] = rule
                rules_added += 1
            
            compliance.save_rules()
            
            return html.Div(f"✅ Успешно загружено {rules_added} правил из файла {filename}!", 
                          style={"color": "#10B981", "fontWeight": "bold"})
        
        except Exception as e:
            return html.Div(f" Ошибка обработки файла: {str(e)}", style={"color": "#EF4444"})
    
    # 9. Экспорт пакета для буровых
    @app.callback(
        Output('download-kb-package', 'data'),
        Output('export-status', 'children'),
        Input('btn-generate-package', 'n_clicks'),
        [State('export-version', 'value'),
         State('export-include-rules', 'value')],
        prevent_initial_call=True
    )
    def generate_export_package(n_clicks, version, include_options):
        if not include_options:
            return None, html.Div("Выберите хотя бы один тип данных для экспорта!", style={"color": "#F59E0B"})
        
        package = {
            "version": version,
            "export_date": datetime.now().isoformat(),
            "rules": []
        }
        
        if 'rules' in include_options:
            for rule in compliance.rules_cache.values():
                package["rules"].append({
                    'rule_id': rule.rule_id,
                    'category': rule.category,
                    'parameter': rule.parameter,
                    'value': rule.value,
                    'unit': rule.unit,
                    'standard_source': rule.standard_source,
                    'priority': rule.priority,
                    'client_hierarchy': rule.client_hierarchy,
                    'description': rule.description,
                    'mandatory': rule.mandatory,
                    'effective_date': rule.effective_date
                })
        
        filename = f"kb_package_v{version}_{datetime.now().strftime('%Y%m%d')}.json"
        
        return (
            dict(content=json.dumps(package, ensure_ascii=False, indent=2), filename=filename),
            html.Div(f"✅ Пакет {filename} успешно сформирован!", style={"color": "#10B981", "fontWeight": "bold"})
        )
    
    # 10. Валидация данных
    @app.callback(
        Output('validation-results', 'children'),
        Input('btn-run-validation', 'n_clicks'),
        prevent_initial_call=True
    )
    def run_validation(n_clicks):
        issues = []
        
        rule_ids = [r.rule_id for r in compliance.rules_cache.values()]
        duplicates = [x for x in rule_ids if rule_ids.count(x) > 1]
        if duplicates:
            issues.append(f"Найдены дубликаты ID: {set(duplicates)}")
        
        for rule in compliance.rules_cache.values():
            if not rule.rule_id or not rule.category or not rule.parameter:
                issues.append(f"Правило {rule.rule_id} имеет пустые обязательные поля")
        
        if not issues:
            return html.Div([
                html.Div("✅ Валидация пройдена успешно! Проблем не обнаружено.", 
                        style={"color": "#10B981", "fontWeight": "bold", "padding": "15px", 
                               "backgroundColor": "#F0FDF4", "borderRadius": "6px", "border": "1px solid #10B981"})
            ])
        
        return html.Div([
            html.Div(f"⚠️ Найдено проблем: {len(issues)}", style={"color": "#F59E0B", "fontWeight": "bold", "marginBottom": "10px"}),
            html.Ul([html.Li(issue, style={"color": "#EF4444", "marginBottom": "5px"}) for issue in issues])
        ], style={"padding": "15px", "backgroundColor": "#FEF2F2", "borderRadius": "6px", "border": "1px solid #EF4444"})
