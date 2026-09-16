"""
МОДУЛЬ ИИ-КОНСУЛЬТАНТА ПО ЭКСПЛУАТАЦИИ ВЗД
Генерирует контекстные рекомендации на основе вендора и параметров
"""
from dash import html
import dash_bootstrap_components as dbc
from modules.vendor_knowledge_base import get_vendor_knowledge


def create_ai_advisor_panel(vendor: str, sand_pct: float, temp_c: float,
                           mud_type: str, wob: float, vibration_g: float,
                           remaining_hours: float) -> html.Div:
    """
    Создает панель ИИ-советника с рекомендациями
    
    Args:
        vendor: Название вендора (Радиус-Сервис, NOV, и т.д.)
        sand_pct: Содержание песка, %
        temp_c: Температура, °C
        mud_type: Тип раствора
        wob: Осевая нагрузка, т
        vibration_g: Вибрация, g
        remaining_hours: Остаточный ресурс, ч
    """
    # Получаем знания о вендоре из базы
    vendor_data = get_vendor_knowledge(vendor)
    
    if not vendor_data:
        # Если вендор не найден — дефолтные рекомендации
        return _create_default_advisor(vendor, remaining_hours)
    
    # Генерируем контекстные рекомендации
    advice_cards = []
    
    # 1. Слабые места вендора
    if vendor_data.get("weak_points"):
        advice_cards.append(_create_card(
            "🔍 Слабые места данного ВЗД",
            [f"• {item}" for item in vendor_data["weak_points"]],
            "#3B82F6"  # Blue
        ))
    
    # 2. Рекомендации по текущим параметрам
    context_advice = []
    
    if sand_pct > 0.5 and "high_sand" in vendor_data.get("recommendations", {}):
        context_advice.append(vendor_data["recommendations"]["high_sand"])
    
    if temp_c > 100 and "high_temp" in vendor_data.get("recommendations", {}):
        context_advice.append(vendor_data["recommendations"]["high_temp"])
    
    if "Кислот" in mud_type and "acid_mud" in vendor_data.get("recommendations", {}):
        context_advice.append(vendor_data["recommendations"]["acid_mud"])
    
    if wob > 15 and "high_wob" in vendor_data.get("recommendations", {}):
        context_advice.append(vendor_data["recommendations"]["high_wob"])
    
    if vibration_g > 2.5 and "high_vibration" in vendor_data.get("recommendations", {}):
        context_advice.append(vendor_data["recommendations"]["high_vibration"])
    
    if context_advice:
        advice_cards.append(_create_card(
            "️ Рекомендации по текущим параметрам",
            [f"• {adv}" for adv in context_advice],
            "#F59E0B"  # Amber
        ))
    
    # 3. Типичные отказы
    if vendor_data.get("typical_failures"):
        advice_cards.append(_create_card(
            " Типичные отказы (статистика)",
            [f"• {failure} ({freq})" for failure, freq in vendor_data["typical_failures"].items()],
            "#10B981"  # Green
        ))
    
    # 4. Оптимальные условия
    if vendor_data.get("optimal_conditions"):
        advice_cards.append(_create_card(
            "✅ Оптимальные условия эксплуатации",
            [vendor_data["optimal_conditions"]],
            "#16A34A"  # Dark Green
        ))
    
    # 5. Средний ресурс по регионам
    if vendor_data.get("avg_lifetime_hours"):
        region_hours = vendor_data["avg_lifetime_hours"]
        advice_cards.append(_create_card(
            "⏱️ Средний ресурс по регионам",
            [f"• {region}: {hours} моточасов" for region, hours in region_hours.items()],
            "#8B5CF6"  # Purple
        ))
    
    # Определяем статус
    if sand_pct > 0.8 or temp_c > 120 or vibration_g > 5.0:
        status_color = "#DC2626"
        status_text = "КРИТИЧЕСКИЕ ПАРАМЕТРЫ"
        status_icon = "🔴"
    elif sand_pct > 0.5 or temp_c > 100 or vibration_g > 2.5:
        status_color = "#F59E0B"
        status_text = "ТРЕБУЕТ ВНИМАНИЯ"
        status_icon = ""
    else:
        status_color = "#10B981"
        status_text = "НОРМАЛЬНЫЙ РЕЖИМ"
        status_icon = "🟢"
    
    return html.Div([
        # Заголовок
        html.Div([
            html.Span(status_icon, style={"fontSize": "24px", "marginRight": "10px"}),
            html.Span("ИИ-КОНСУЛЬТАНТ ПО ЭКСПЛУАТАЦИИ ВЗД", 
                     style={"fontWeight": "bold", "fontSize": "16px", "color": "#0F172A"}),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "15px"}),
        
        # Статус параметров
        html.Div(status_text, 
                style={"backgroundColor": status_color, "color": "white", "padding": "10px",
                      "borderRadius": "4px", "textAlign": "center", "fontWeight": "bold",
                      "marginBottom": "20px"}),
        
        # Карточки рекомендаций
        *advice_cards,
        
        # Прогноз ресурса
        html.Div([
            html.H6("📊 Прогноз остаточного ресурса:", 
                   style={"fontWeight": "bold", "marginBottom": "10px"}),
            html.Div(f"{remaining_hours:.1f} моточасов", 
                    style={"fontSize": "28px", "fontWeight": "bold", "color": status_color}),
            html.Small("При сохранении текущих параметров", 
                      style={"color": "#64748B"})
        ], style={"backgroundColor": "#F1F5F9", "padding": "15px", "borderRadius": "6px",
                 "textAlign": "center", "marginTop": "15px"})
    ], style={"padding": "20px", "backgroundColor": "white", "borderRadius": "8px",
             "border": "2px solid #E2E8F0"})


def _create_card(category: str, items: list, color: str) -> html.Div:
    """Создает карточку рекомендации"""
    return html.Div([
        html.Div(category, 
                style={"fontWeight": "bold", "fontSize": "14px", "marginBottom": "10px", 
                       "color": color, "borderBottom": f"2px solid {color}",
                       "paddingBottom": "5px"}),
        html.Ul([html.Li(item, style={"margin": "5px 0", "fontSize": "13px", "lineHeight": "1.5"}) 
                for item in items],
               style={"paddingLeft": "20px", "margin": "0"})
    ], style={"backgroundColor": "#F8FAFC", "padding": "15px", "borderRadius": "6px", 
             "marginBottom": "15px", "border": f"1px solid {color}"})


def _create_default_advisor(vendor: str, remaining_hours: float) -> html.Div:
    """Дефолтные рекомендации для неизвестных вендоров"""
    return html.Div([
        html.Div("⚠️ Вендор не найден в базе знаний", 
                style={"fontWeight": "bold", "fontSize": "16px", "marginBottom": "15px", 
                       "color": "#F59E0B"}),
        html.Ul([
            html.Li("Требуется усиленный контроль параметров"),
            html.Li("Фиксировать все параметры для накопления статистики"),
            html.Li("Проводить дефектоскопию каждые 50 моточасов")
        ], style={"paddingLeft": "20px", "marginBottom": "15px"}),
        html.Div(f"Прогноз ресурса: {remaining_hours:.1f} моточасов",
                style={"fontSize": "18px", "fontWeight": "bold"})
    ], style={"padding": "20px", "backgroundColor": "#FEF3C7", "borderRadius": "8px",
             "border": "2px solid #F59E0B"})


def ai_advisor_callbacks(app, data_bridge):
    """
    Регистрирует callback'ы для ИИ-советника
    
    Этот callback обновляет панель автоматически при изменении параметров
    """
    from dash import Input, Output
    
    @app.callback(
        Output('ai-advisor-output', 'children'),
        [Input('vzd-vendor', 'value'),
         Input('vzd-mud-density', 'value'),
         Input('vzd-radial-ich', 'value'),
         Input('vzd-hours', 'value')]
    )
    def update_ai_advisor(vendor, mud_density, radial_ich, vzd_hours):
        # Защита от None
        if None in [vendor, mud_density, radial_ich, vzd_hours]:
            return html.P("Введите параметры для генерации рекомендаций")
        
        # Примерные значения (в реальности брать из data_bridge)
        temp_c = 90.0 + (mud_density * 10)
        sand_pct = 0.5
        mud_type = "Полимерный"
        wob = 12.0
        vibration_g = (radial_ich ** 2) * 4.5 * (mud_density / 1.15)
        remaining_hours = max(0, 200 - vzd_hours - ((radial_ich * 10)))
        
        return create_ai_advisor_panel(
            vendor=vendor,
            sand_pct=sand_pct,
            temp_c=temp_c,
            mud_type=mud_type,
            wob=wob,
            vibration_g=vibration_g,
            remaining_hours=remaining_hours
        )
