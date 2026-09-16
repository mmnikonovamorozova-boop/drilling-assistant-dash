"""
ИНТЕРФЕЙС СИНХРОНИЗАЦИИ ДЛЯ ИНЖЕНЕРА В ОФИСЕ
Три простые кнопки для центрального узла
"""
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from modules.office_sync import OfficeSyncManager


def create_office_sync_panel():
    """
    Создает панель синхронизации для офиса
    """
    sync_manager = OfficeSyncManager()
    stats = sync_manager.get_sync_statistics()
    
    return html.Div([
        # Заголовок
        html.H4("🏢 Центральный узел синхронизации", 
                style={"color": "#0f172a", "marginBottom": "10px", "textAlign": "center"}),
        
        html.P("Агрегация данных со всех буровых и обновление базы знаний",
              style={"color": "#64748b", "marginBottom": "20px", "textAlign": "center"}),
        
        # Статистика
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div("Всего записей", style={"fontSize": "12px", "color": "#64748b"}),
                    html.Div(f"{stats['total_records']}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0f172a"})
                ], style={"backgroundColor": "#f1f5f9", "padding": "15px", "borderRadius": "6px", "textAlign": "center"})
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Div("Буровых подключено", style={"fontSize": "12px", "color": "#64748b"}),
                    html.Div(f"{stats['unique_burovayas']}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0f172a"})
                ], style={"backgroundColor": "#f1f5f9", "padding": "15px", "borderRadius": "6px", "textAlign": "center"})
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Div("Последняя синхронизация", style={"fontSize": "12px", "color": "#64748b"}),
                    html.Div(stats['recent_syncs'][0]['timestamp'][:19] if stats['recent_syncs'] else "Нет данных", 
                            style={"fontSize": "14px", "fontWeight": "bold", "color": "#0f172a"})
                ], style={"backgroundColor": "#f1f5f9", "padding": "15px", "borderRadius": "6px", "textAlign": "center"})
            ], width=4),
        ], className="mb-4"),
        
        html.Hr(),
        
        # КНОПКА 1: Импорт данных с буровых
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span("📥 ", style={"fontSize": "24px"}),
                    html.Span("1. Импорт данных с буровых", style={"fontWeight": "bold", "fontSize": "16px"})
                ])
            ]),
            dbc.CardBody([
                html.P("Загрузите JSON-файлы с флешек от буровых",
                      style={"color": "#64748b", "fontSize": "13px", "marginBottom": "15px"}),
                
                dcc.Upload(
                    id='upload-burovaya-files',
                    children=html.Div([
                        ' Перетащите файлы DDR_export_*.json сюда или ',
                        html.A('выберите файлы', style={"color": "#2563eb", "fontWeight": "bold"})
                    ]),
                    style={
                        'width': '100%',
                        'height': '80px',
                        'lineHeight': '80px',
                        'borderWidth': '2px',
                        'borderStyle': 'dashed',
                        'borderRadius': '8px',
                        'textAlign': 'center',
                        'backgroundColor': '#f8fafc',
                        'marginBottom': '10px'
                    },
                    multiple=True  # Можно загружать несколько файлов
                ),
                
                dbc.Button("📥 Импортировать данные", 
                          id='btn-import-burovaya',
                          color="primary",
                          size="lg",
                          className="w-100"),
                html.Div(id='import-burovaya-status', style={"marginTop": "10px"}),
            ])
        ], className="mb-3"),
        
        # КНОПКА 2: Объединить все базы
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span(" ", style={"fontSize": "24px"}),
                    html.Span("2. Объединить все базы", style={"fontWeight": "bold", "fontSize": "16px"})
                ])
            ]),
            dbc.CardBody([
                html.P("Агрегация данных и пересчет статистики по вендорам",
                      style={"color": "#64748b", "fontSize": "13px", "marginBottom": "15px"}),
                dbc.Button("🔀 Объединить базы", 
                          id='btn-merge-bases',
                          color="success",
                          size="lg",
                          className="w-100"),
                html.Div(id='merge-bases-status', style={"marginTop": "10px"}),
            ])
        ], className="mb-3"),
        
        # КНОПКА 3: Экспорт центральной базы
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span("📤 ", style={"fontSize": "24px"}),
                    html.Span("3. Экспорт центральной базы", style={"fontWeight": "bold", "fontSize": "16px"})
                ])
            ]),
            dbc.CardBody([
                html.P("Создание файла central_update.json для развоза по буровым",
                      style={"color": "#64748b", "fontSize": "13px", "marginBottom": "15px"}),
                dbc.Button("📤 Экспортировать для развоза", 
                          id='btn-export-central',
                          color="warning",
                          size="lg",
                          className="w-100"),
                html.Div(id='export-central-status', style={"marginTop": "10px"}),
            ])
        ], className="mb-3"),
        
        # Инструкция
        html.Div([
            html.H6("📋 Workflow инженера в офисе:", style={"marginBottom": "10px"}),
            html.Ol([
                html.Li("Получите флешки от буровых (раз в месяц)"),
                html.Li("Нажмите 'Импорт данных с буровых' — загрузите все JSON-файлы"),
                html.Li("Нажмите 'Объединить все базы' — система пересчитает статистику"),
                html.Li("Нажмите 'Экспорт центральной базы' — получите файл для развоза"),
                html.Li("Скопируйте central_update_*.json на флешки"),
                html.Li("Развезите флешки по буровым"),
            ], style={"fontSize": "12px", "color": "#64748b", "paddingLeft": "20px"})
        ], style={"backgroundColor": "#f1f5f9", "padding": "15px", "borderRadius": "6px", "marginTop": "20px"}),
    ], style={"padding": "20px", "maxWidth": "800px", "margin": "0 auto"})


def office_sync_callbacks(app, data_bridge):
    """
    Callback'ы для кнопок офисной синхронизации
    """
    sync_manager = OfficeSyncManager()
    
    # КНОПКА 1: Импорт данных с буровых
    @app.callback(
        Output('import-burovaya-status', 'children'),
        Input('btn-import-burovaya', 'n_clicks'),
        State('upload-burovaya-files', 'contents'),
        State('upload-burovaya-files', 'filename'),
        prevent_initial_call=True
    )
    def import_burovaya_data(n_clicks, contents_list, filenames_list):
        if n_clicks is None or contents_list is None:
            return html.Div("⚠️ Сначала выберите файлы", style={"color": "#f59e0b"})
        
        messages = []
        
        for content, filename in zip(contents_list, filenames_list):
            # Сохранение временного файла
            import base64
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            
            temp_path = Path(f"data/temp_{filename}")
            temp_path.write_bytes(decoded)
            
            # Импорт
            success, message = sync_manager.import_from_burovaya(str(temp_path))
            messages.append(message)
            
            # Удаление временного файла
            temp_path.unlink()
        
        # Отображение результатов
        return html.Div([
            html.Div(msg, style={"color": "#16a34a" if "✅" in msg else "#dc2626", 
                                "fontWeight": "bold", "marginBottom": "5px"})
            for msg in messages
        ])
    
    # КНОПКА 2: Объединить все базы
    @app.callback(
        Output('merge-bases-status', 'children'),
        Input('btn-merge-bases', 'n_clicks'),
        prevent_initial_call=True
    )
    def merge_bases(n_clicks):
        if n_clicks is None:
            return ""
        
        success, message = sync_manager.merge_all_bases()
        
        if success:
            return html.Div(message, style={"color": "#16a34a", "fontWeight": "bold"})
        else:
            return html.Div(message, style={"color": "#dc2626", "fontWeight": "bold"})
    
    # КНОПКА 3: Экспорт центральной базы
    @app.callback(
        Output('export-central-status', 'children'),
        Input('btn-export-central', 'n_clicks'),
        prevent_initial_call=True
    )
    def export_central(n_clicks):
        if n_clicks is None:
            return ""
        
        success, message, filepath = sync_manager.export_central_update()
        
        if success:
            return html.Div([
                html.Div(message, style={"color": "#16a34a", "fontWeight": "bold", "marginBottom": "5px"}),
                html.Small(f"Файл: {filepath}", style={"color": "#64748b"}),
            ])
        else:
            return html.Div(message, style={"color": "#dc2626", "fontWeight": "bold"})
