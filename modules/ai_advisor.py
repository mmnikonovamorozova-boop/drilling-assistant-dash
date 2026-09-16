"""
МОДУЛЬ ИИ-КОНСУЛЬТАНТА ПО ЭКСПЛУАТАЦИИ ВЗД
Генерирует контекстные рекомендации на основе:
- Вендора двигателя
- Исторических паттернов отказов
- Текущих параметров бурения
"""
from typing import List, Dict
from dash import html
import dash_bootstrap_components as dbc

# ============================================================================
# БАЗА ЗНАНИЙ: СЛАБЫЕ МЕСТА ПО ВЕНДОРАМ (СТО ИНТИ S.QS.7)
# ============================================================================
VENDOR_KNOWLEDGE_BASE = {
    "Радиус-Сервис": {
        "слабые_места": [
            "Шпиндельная секция (подшипники скольжения)",
            "Вал-шестерня (контактная усталость)",
            "Радиальные уплотнения вала",
        ],
        "рекомендации": {
            "высокий_песок": "При содержании песка >0.5% критически ускоряется износ подшипников шпинделя. Рекомендуется сократить интервал бурения на 20% и контролировать вибрацию каждые 50 моточасов.",
            "высокая_температура": "Двигатели Радиус-Сервис при T > 110°C демонстрируют ускоренную деградацию эластомеров статора (NBR). Рекомендуется использовать термостойкие пачки и контролировать температуру на забое.",
            "кислотная_среда": "Кислотные пачки вызывают коррозию радиальных уплотнений вала. После прокачки кислоты обязательна дефектоскопия уплотнений.",
            "высокий_момент": "При WOB > 15 тонн наблюдается повышенный износ вал-шестерни. Рекомендуется чередовать осевую нагрузку.",
        },
        "типичные_отказы": [
            "Задиры подшипников скольжения (60% случаев)",
            "Разрушение уплотнений вала (25% случаев)",
            "Усталостное разрушение шлицевого соединения (15% случаев)",
        ],
        "оптимальные_условия": "Песок <0.4%, T < 100°C, WOB 8-12 тонн, полимерный раствор",
    },
    
    "ВНИИБТ-БИ": {
        "слабые_места": [
            "Статор (термическая деструкция резины)",
            "Ротор (абразивный износ хромового покрытия)",
            "Перепускной клапан",
        ],
        "рекомендации": {
            "высокий_песок": "ВНИИБТ-БИ чувствительны к абразивному износу ротора. При песке >0.5% рекомендуется установка дополнительных гидроциклонов.",
            "высокая_температура": "Статоры ВНИИБТ-БИ имеют пониженную термостойкость (до 120°C). При превышении — риск вздутия резины и потери герметичности камер.",
            "высокий_расход": "При Q > 35 л/с наблюдается эрозия перепускного клапана. Контролировать перепад давления.",
        },
        "типичные_отказы": [
            "Вздутие и растрескивание статора (45% случаев)",
            "Износ хромового покрытия ротора (30% случаев)",
            "Заклинивание перепускного клапана (25% случаев)",
        ],
        "оптимальные_условия": "Песок <0.3%, T < 110°C, Q 20-30 л/с, гипсокалиевый раствор",
    },
    
    "Зарубежный импорт": {
        "слабые_места": [
            "Электроника (при наличии датчиков)",
            "Подшипники качения",
            "Соединительные муфты",
        ],
        "рекомендации": {
            "высокая_температура": "Импортные ВЗД (Smith, Baker Hughes) имеют лучшую термостойкость (до 150°C), но чувствительны к термоударам. Избегать резких изменений температуры.",
            "вибрация": "При вибрации > 5g наблюдается усталостное разрушение подшипников качения. Рекомендуется установка гасителей вибрации.",
        },
        "типичные_отказы": [
            "Отказ подшипников качения (40% случаев)",
            "Повреждение электронной начинки (30% случаев)",
            "Разрушение муфт (30% случаев)",
        ],
        "оптимальные_условия": "T < 130°C, вибрация < 3g, стандартный API раствор",
    },
}

# ============================================================================
# АНАЛИЗАТОР ПАРАМЕТРОВ И ГЕНЕРАТОР РЕКОМЕНДАЦИЙ
# ============================================================================

def analyze_operating_conditions(sand_pct: float, temp_c: float, mud_type: str, 
                                 wob: float, vibration_g: float) -> Dict[str, any]:
    """
    Анализирует текущие условия эксплуатации и определяет риски
    """
    risks = []
    priority = "LOW"
    
    # Анализ песка
    if sand_pct > 0.8:
        risks.append({
            "type": "CRITICAL",
            "param": "Песок",
            "value": f"{sand_pct:.2f}%",
            "message": "Критическое содержание абразива!",
            "action": "Срочно активировать все ступени очистки. Рассмотреть снижение ROP."
        })
        priority = "CRITICAL"
    elif sand_pct > 0.5:
        risks.append({
            "type": "WARNING",
            "param": "Песок",
            "value": f"{sand_pct:.2f}%",
            "message": "Повышенное содержание песка",
            "action": "Усилить контроль гидроциклонов. Проверить работу сит."
        })
        if priority != "CRITICAL":
            priority = "WARNING"
    
    # Анализ температуры
    if temp_c > 120:
        risks.append({
            "type": "CRITICAL",
            "param": "Температура",
            "value": f"{temp_c:.0f}°C",
            "message": "Превышен термический предел для большинства ВЗД!",
            "action": "Увеличить расход для охлаждения. Рассмотреть термопачку."
        })
        priority = "CRITICAL"
    elif temp_c > 100:
        risks.append({
            "type": "WARNING",
            "param": "Температура",
            "value": f"{temp_c:.0f}°C",
            "message": "Повышенная температура",
            "action": "Контролировать деградацию эластомеров."
        })
        if priority not in ["CRITICAL", "WARNING"]:
            priority = "WARNING"
    
    # Анализ типа раствора
    if "Кислот" in mud_type or "Acid" in mud_type:
        risks.append({
            "type": "WARNING",
            "param": "Раствор",
            "value": mud_type,
            "message": "Агрессивная среда!",
            "action": "После прокачки обязательна дефектоскопия уплотнений ВЗД."
        })
        if priority != "CRITICAL":
            priority = "WARNING"
    
    # Анализ вибрации
    if vibration_g > 5.0:
        risks.append({
            "type": "CRITICAL",
            "param": "Вибрация",
            "value": f"{vibration_g:.1f}g",
            "message": "Критическая вибрация!",
            "action": "Снизить WOB и RPM. Проверить центровку КНБК."
        })
        priority = "CRITICAL"
    elif vibration_g > 2.5:
        risks.append({
            "type": "INFO",
            "param": "Вибрация",
            "value": f"{vibration_g:.1f}g",
            "message": "Повышенная вибрация",
            "action": "Контролировать усталостные разрушения."
        })
    
    return {
        "priority": priority,
        "risks": risks,
        "safe_to_drill": priority != "CRITICAL"
    }


def generate_vendor_advice(vendor: str, sand_pct: float, temp_c: float, 
                          mud_type: str, wob: float, vibration_g: float) -> List[Dict]:
    """
    Генерирует персонализированные рекомендации для конкретного вендора
    """
    advice_list = []
    vendor_data = VENDOR_KNOWLEDGE_BASE.get(vendor, VENDOR_KNOWLEDGE_BASE["Радиус-Сервис"])
    
    # Базовые рекомендации по слабым местам
    advice_list.append({
        "category": "🔍 Слабые места данного ВЗД",
        "icon": "⚙️",
        "items": [f"• {item}" for item in vendor_data["слабые_места"]],
        "color": "#3B82F6"  # Blue
    })
    
    # Контекстные рекомендации на основе параметров
    context_advice = []
    
    if sand_pct > 0.5:
        context_advice.append(vendor_data["рекомендации"].get("высокий_песок", ""))
    
    if temp_c > 100:
        context_advice.append(vendor_data["рекомендации"].get("высокая_температура", ""))
    
    if "Кислот" in mud_type:
        context_advice.append(vendor_data["рекомендации"].get("кислотная_среда", ""))
    
    if wob > 15:
        context_advice.append(vendor_data["рекомендации"].get("высокий_момент", ""))
    
    if vibration_g > 2.5:
        context_advice.append(vendor_data["рекомендации"].get("вибрация", ""))
    
    if context_advice:
        advice_list.append({
            "category": "️ Рекомендации по текущим параметрам",
            "icon": "📊",
            "items": [f"• {adv}" for adv in context_advice if adv],
            "color": "#F59E0B"  # Amber
        })
    
    # Типичные отказы для справки
    advice_list.append({
        "category": "📋 Типичные отказы (статистика СТО ИНТИ)",
        "icon": "",
        "items": [f"• {failure}" for failure in vendor_data["типичные_отказы"]],
        "color": "#10B981"  # Green
    })
    
    # Оптимальные условия
    advice_list.append({
        "category": "✅ Оптимальные условия эксплуатации",
        "icon": "🎯",
        "items": [vendor_data["оптимальные_условия"]],
        "color": "#16A34A"  # Dark Green
    })
    
    return advice_list


def create_ai_advisor_panel(vendor: str, sand_pct: float, temp_c: float,
                           mud_type: str, wob: float, vibration_g: float,
                           remaining_hours: float) -> html.Div:
    """
    Создает панель ИИ-советника с рекомендациями
    """
    # Анализ условий
    analysis = analyze_operating_conditions(sand_pct, temp_c, mud_type, wob, vibration_g)
    
    # Генерация рекомендаций
    advice_cards = generate_vendor_advice(vendor, sand_pct, temp_c, mud_type, wob, vibration_g)
    
    # Определение цвета статуса
    if analysis["priority"] == "CRITICAL":
        status_color = "#DC2626"
        status_text = "КРИТИЧЕСКИЕ ПАРАМЕТРЫ"
        status_icon = "🔴"
    elif analysis["priority"] == "WARNING":
        status_color = "#F59E0B"
        status_text = "ТРЕБУЕТ ВНИМАНИЯ"
        status_icon = "🟡"
    else:
        status_color = "#10B981"
        status_text = "НОРМАЛЬНЫЙ РЕЖИМ"
        status_icon = "🟢"
    
    # Создание карточек рекомендаций
    advice_html = []
    
    for card in advice_cards:
        card_component = html.Div([
            html.Div(card["category"], 
                    style={"fontWeight": "bold", "fontSize": "14px", "marginBottom": "10px", 
                           "color": card["color"], "borderBottom": f"2px solid {card["color"]}",
                           "paddingBottom": "5px"}),
            html.Ul([html.Li(item, style={"margin": "5px 0", "fontSize": "13px", "lineHeight": "1.5"}) 
                    for item in card["items"]],
                   style={"paddingLeft": "20px", "margin": "0"})
        ], style={"backgroundColor": "#F8FAFC", "padding": "15px", "borderRadius": "6px", 
                 "marginBottom": "15px", "border": f"1px solid {card["color"]}"})
        advice_html.append(card_component)
    
    return html.Div([
        # Заголовок с статусом
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
        
        # Риски (если есть)
        *([html.Div([
            html.H6("⚠️ Выявленные риски:", style={"color": "#DC2626", "marginBottom": "10px"}),
            *[html.Div([
                html.Span(f"{risk['param']}: {risk['value']}", style={"fontWeight": "bold"}),
                html.Br(),
                html.Span(risk['message'], style={"color": "#DC2626"}),
                html.Br(),
                html.Small(risk['action'], style={"color": "#64748B"}),
                html.Hr(style={"margin": "10px 0"})
            ], style={"marginBottom": "10px"}) for risk in analysis["risks"]]
        ], style={"backgroundColor": "#FEF2F2", "padding": "15px", "borderRadius": "6px",
                 "border": "1px solid #DC2626", "marginBottom": "20px"})] if analysis["risks"] else []),
        
        # Карточки рекомендаций
        *advice_html,
        
        # Прогноз ресурса
        html.Div([
            html.H6(" Прогноз остаточного ресурса:", 
                   style={"fontWeight": "bold", "marginBottom": "10px"}),
            html.Div(f"{remaining_hours:.1f} моточасов", 
                    style={"fontSize": "28px", "fontWeight": "bold", "color": status_color}),
            html.Small("При сохранении текущих параметров", 
                      style={"color": "#64748B"})
        ], style={"backgroundColor": "#F1F5F9", "padding": "15px", "borderRadius": "6px",
                 "textAlign": "center", "marginTop": "15px"})
    ], style={"padding": "20px", "backgroundColor": "white", "borderRadius": "8px",
             "border": "2px solid #E2E8F0"})


# ============================================================================
# CALLBACKS
# ============================================================================

def ai_advisor_callbacks(app, data_bridge):
    """
    Регистрирует callback'ы для ИИ-советника
    """
    @app.callback(
        Output('ai-advisor-output', 'children'),
        [Input('vzd-vendor', 'value'),
         Input('vzd-mud-density', 'value'),
         Input('vzd-radial-ich', 'value'),
         Input('vzd-hours', 'value'),
         Input('umk-torque-target', 'value'),  # Используем как proxy для WOB
         Input('vzd-size-a', 'value'),
         Input('vzd-size-b', 'value')]
    )
    def update_ai_advisor(vendor, mud_density, radial_ich, vzd_hours, 
                         torque_target, size_a, size_b):
        # Защита от None
        if None in [vendor, mud_density, radial_ich, vzd_hours]:
            return html.P("Введите параметры для генерации рекомендаций")
        
        # Примерные значения для демонстрации (в реальности брать из data_bridge)
        temp_c = 90.0 + (mud_density * 10)  # Условная температура
        mud_type = "Полимерный"
        wob = (torque_target if torque_target else 50) / 3  # Примерный WOB
        vibration_g = (radial_ich ** 2) * 4.5 * (mud_density / 1.15)
        
        # Расчет остаточного ресурса (упрощенно)
        axial_delta = (size_a - size_b) if size_a and size_b else 4.5
        remaining_hours = max(0, 200 - vzd_hours - (axial_delta * 10))
        
        # Генерация панели
        return create_ai_advisor_panel(
            vendor=vendor,
            sand_pct=0.5,  # Взять из data_bridge
            temp_c=temp_c,
            mud_type=mud_type,
            wob=wob,
            vibration_g=vibration_g,
            remaining_hours=remaining_hours
        )
