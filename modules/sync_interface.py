"""
ИНТЕРФЕЙС СИНХРОНИЗАЦИИ ДЛЯ БУРОВИКОВ
Три простые кнопки без лишних деталей
"""
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from modules.sync_manager import SyncManager


def create_sync_panel():
    """
    Создает панель синхронизации с тремя кнопками
    """
    return html.Div([
        # Заголовок
        html.H4("💾 Синхронизация данных", 
                style={"color": "#0f172a", "marginBottom": "20px", "textAlign": "center"}),
        
        html.P("Выберите действие для обмена данными с центральной базой",
              style={"color": "#64748b", "marginBottom": "20px", "textAlign": "center"}),
        
        html.Hr(style={"marginBottom": "30px"}),
        
        # КНОПКА 1: Выгрузить DDR
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span("📊 ", style={"fontSize": "24px"}),
                    html.Span("1. Выгрузить DDR", style={"fontWeight": "bold", "fontSize": "16px"})
                ])
            ]),
            dbc.CardBody([
                html.P("Экспорт данных из дейликов для отправки в офис",
                      style={"color": "#64748b", "fontSize": "13px", "marginBottom": "15px"}),
                dbc.Button("📥 Выгрузить DDR", 
                          id='btn-export-ddr',
                          color="primary",
                          size="lg",
                          className="w-100"),
                html.Div(id='ddr-export-status', style={"marginTop": "10px"}),
            ])
        ], className="mb-3"),
        
        # КНОПКА 2: Экспорт данных
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span(" ", style={"fontSize": "24px"}),
                    html.Span("2. Экспорт данных", style={"fontWeight": "bold", "fontSize": "16px"})
                ])
            ]),
            dbc.CardBody([
                html.P("Полный экспорт базы знаний (SQLite + метаданные)",
                      style={"color": "#64748b", "fontSize": "13px", "marginBottom": "15px"}),
                dbc.Button("💿 Экспорт данных", 
                          id='btn-export-full',
                          color="success",
                          size="lg",
                          className="w-100"),
                html.Div(id='full-export-status', style={"marginTop": "10px"}),
            ])
        ], className="mb-3"),
        
        # КНОПКА 3: Обновить базу знаний
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span("🔄 ", style={"fontSize": "24px"}),
                    html.Span("3. Обновить базу знаний", style={"fontWeight": "bold", "fontSize": "16px"})
                ])
            ]),
            dbc.CardBody([
                html.P("Загрузка обновлений из центральной базы (с флешки)",
                      style={"color": "#64748b", "fontSize": "13px", "marginBottom": "15px"}),
                
                dcc.Upload(
                    id='upload-central-update',
                    children=html.Div([
                        '📂 Выберите файл central_update.json или ',
                        html.A('перетащите сюда', style={"color": "#2563eb", "fontWeight": "bold"})
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '2px',
                        'borderStyle': 'dashed',
                        'borderRadius': '8px',
                        'textAlign': 'center',
                        'backgroundColor': '#f8fafc',
                        'marginBottom': '10px'
                    },
                    multiple=False
                ),
                
                dbc.Button("🔄 Обновить базу знаний", 
                          id='btn-import-update',
                          color="warning",
                          size="lg",
                          className="w-100"),
                html.Div(id='import-update-status', style={"marginTop": "10px"}),
            ])
        ], className="mb-3"),
        
        # Скрытое хранилище для путей к файлам
        dcc.Store(id='sync-file-path-storage'),
        
        # Инструкции
        html.Div([
            html.H6("📋 Инструкция:", style={"marginBottom": "10px"}),
            html.Ol([
                html.Li("Раз в неделю нажимайте 'Выгрузить DDR'"),
                html.Li("При вахте копируйте файлы на флешку"),
                html.Li("В офисе инженер объединит все базы"),
                html.Li("Получите файл central_update.json"),
                html.Li("Нажмите 'Обновить базу знаний'"),
            ], style={"fontSize": "12px", "color": "#64748b", "paddingLeft": "20px"})
        ], style={"backgroundColor": "#f1f5f9", "padding": "15px", "borderRadius": "6px", "marginTop": "20px"}),
    ], style={"padding": "20px", "maxWidth": "600px", "margin": "0 auto"})


def sync_callbacks(app, data_bridge):
    """
    Callback'ы для кнопок синхронизации
    """
    sync_manager = SyncManager()
    
    # КНОПКА 1: Выгрузить DDR
    @app.callback(
        Output('ddr-export-status', 'children'),
        Input('btn-export-ddr', 'n_clicks'),
        prevent_initial_call=True
    )
    def export_ddr(n_clicks):
        if n_clicks is None:
            return ""
        
        success, message, filepath = sync_manager.export_ddr_data()
        
        if success:
            return html.Div([
                html.Div(message, style={"color": "#16a34a", "fontWeight": "bold", "marginBottom": "5px"}),
                html.Small(f"Файл сохранен: {filepath}", style={"color": "#64748b"}),
            ])
        else:
            return html.Div(message, style={"color": "#dc2626", "fontWeight": "bold"})
    
    # КНОПКА 2: Экспорт данных
    @app.callback(
        Output('full-export-status', 'children'),
        Input('btn-export-full', 'n_clicks'),
        prevent_initial_call=True
    )
    def export_full(n_clicks):
        if n_clicks is None:
            return ""
        
        success, message, filepath = sync_manager.export_full_database()
        
        if success:
            return html.Div([
                html.Div(message, style={"color": "#16a34a", "fontWeight": "bold", "marginBottom": "5px"}),
                html.Small(f"Файл: {filepath}", style={"color": "#64748b"}),
            ])
        else:
            return html.Div(message, style={"color": "#dc2626", "fontWeight": "bold"})
    
    # КНОПКА 3: Обновить базу знаний (через Upload)
    @app.callback(
        Output('import-update-status', 'children'),
        Input('btn-import-update', 'n_clicks'),
        State('upload-central-update', 'contents'),
        State('upload-central-update', 'filename'),
        prevent_initial_call=True
    )
    def import_update(n_clicks, contents, filename):
        if n_clicks is None or contents is None:
            return html.Div("⚠️ Сначала выберите файл обновления", style={"color": "#f59e0b"})
        
        # Сохранение загруженного файла
        import base64
        from pathlib import Path
        
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        temp_path = Path(f"data/temp_{filename}")
        temp_path.write_bytes(decoded)
        
        # Импорт данных
        success, message = sync_manager.import_central_knowledge(str(temp_path))
        
        # Удаление временного файла
        temp_path.unlink()
        
        if success:
            return html.Div([
                html.Div(message, style={"color": "#16a34a", "fontWeight": "bold"}),
            ])
        else:
            return html.Div(message, style={"color": "#dc2626", "fontWeight": "bold"})
