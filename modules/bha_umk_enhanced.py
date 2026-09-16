"""
УЛУЧШЕННЫЙ МОДУЛЬ УМК С ИСПРАВЛЕННОЙ МАТЕМАТИКОЙ
- Справочник API RP 7G для моментов затяжки
- Правильный расчёт предела скручивания замка
- Исправленная размерность для гидравлики
- Коэффициент из паспорта ключа
- Учёт диаметра каната и площади поршня
"""
import math
import logging
from dataclasses import dataclass
from typing import Tuple, Dict
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# СПРАВОЧНИК API RP 7G: Рекомендуемые моменты затяжки (кН·м)
# Формат: {тип_резьбы: {группа_прочности: момент}}
# ============================================================================
API_RP_7G_TORQUE_TABLE: Dict[str, Dict[str, float]] = {
    "NC26 (2-3/8'')": {"D": 8.1, "E": 10.8, "X": 14.9, "G": 15.6, "S": 20.0},
    "NC31 (2-7/8'')": {"D": 11.5, "E": 15.3, "X": 21.0, "G": 22.0, "S": 28.2},
    "NC38 (3-1/2'')": {"D": 16.9, "E": 22.6, "X": 31.1, "G": 32.5, "S": 41.7},
    "NC46 (4'')":      {"D": 26.4, "E": 35.3, "X": 48.5, "G": 50.8, "S": 65.1},
    "NC50 (4-1/2'')":  {"D": 36.6, "E": 48.8, "X": 67.1, "G": 70.2, "S": 90.0},
    "6-5/8 FH":        {"D": 48.1, "E": 64.1, "X": 88.2, "G": 92.3, "S": 118.3},
    "7-5/8 FH":        {"D": 65.1, "E": 86.8, "X": 119.3, "G": 124.9, "S": 160.1},
}

# Геометрия замков для расчёта предела скручивания (D наружный, d внутренний, мм)
TOOL_JOINT_GEOMETRY: Dict[str, Tuple[float, float]] = {
    "NC26 (2-3/8'')": (88.9, 50.8),
    "NC31 (2-7/8'')": (104.8, 57.2),
    "NC38 (3-1/2'')": (114.3, 63.5),
    "NC46 (4'')":      (127.0, 71.4),
    "NC50 (4-1/2'')":  (152.4, 76.2),
    "6-5/8 FH":        (165.1, 76.2),
    "7-5/8 FH":        (193.7, 82.6),
}

# Группы прочности стали (API Spec 5DP), предел текучести в МПа
STEEL_GRADES_DB: Dict[str, float] = {
    "D": 379,
    "E": 517,
    "X": 689,
    "G": 724,
    "S": 931,
}

# Модели ключей УМК (паспортные данные)
KEY_MODELS_DB: Dict[str, Dict] = {
    "УМК-10/1": {"max_torque": 10.0, "lever_arm": 0.615, "piston_area_cm2": 25.0},
    "УМК-35":   {"max_torque": 35.0, "lever_arm": 0.900, "piston_area_cm2": 40.0},
    "УМК-48":   {"max_torque": 48.0, "lever_arm": 1.100, "piston_area_cm2": 50.0},
    "УМК-75":   {"max_torque": 75.0, "lever_arm": 1.400, "piston_area_cm2": 65.0},
    "УМК-90":   {"max_torque": 90.0, "lever_arm": 1.400, "piston_area_cm2": 80.0},
}

# Коэффициенты трения для смазок (СТО ИНТИ S.QS.8)
GREASE_FACTORS: Dict[str, float] = {
    "Стандартная API (K=1.0)": 1.0,
    "Графитовая (K=1.15)": 1.15,
    "Тефлоновая (K=0.85)": 0.85,
    "Медная специальная (K=1.3)": 1.3,
}


@dataclass
class UMKParameters:
    """Параметры для расчёта УМК"""
    key_model: str
    thread_type: str
    steel_grade: str
    grease_type: str
    lever_arm: float          # м
    k_factor: float           # коэффициент из паспорта ключа
    cable_diameter: float     # мм (для гидравлики)
    piston_area_cm2: float    # см² (площадь поршня гидроцилиндра)
    target_torque_override: float = 0.0  # 0 = использовать API, иначе ручной ввод


class UMKCalculator:
    """Калькулятор момента затяжки УМК с корректной физикой"""

    def __init__(self, params: UMKParameters):
        self.params = params
        self.validation_errors: list = []

    def validate_inputs(self) -> bool:
        """Валидация входных данных"""
        self.validation_errors = []
        if not (0.1 <= self.params.lever_arm <= 5.0):
            self.validation_errors.append("Плечо рычага должно быть 0.1–5.0 м")
        if not (0.5 <= self.params.k_factor <= 2.0):
            self.validation_errors.append("Коэффициент паспорта должен быть 0.5–2.0")
        if not (5.0 <= self.params.cable_diameter <= 50.0):
            self.validation_errors.append("Диаметр каната должен быть 5–50 мм")
        if not (10.0 <= self.params.piston_area_cm2 <= 200.0):
            self.validation_errors.append("Площадь поршня должна быть 10–200 см²")
        if self.params.thread_type not in API_RP_7G_TORQUE_TABLE:
            self.validation_errors.append("Неизвестный тип резьбы")
        if self.params.steel_grade not in STEEL_GRADES_DB:
            self.validation_errors.append("Неизвестная группа прочности стали")
        return len(self.validation_errors) == 0

    def get_recommended_torque(self) -> float:
        """Получить рекомендуемый момент из API RP 7G"""
        if self.params.target_torque_override > 0:
            return self.params.target_torque_override
        table = API_RP_7G_TORQUE_TABLE.get(self.params.thread_type, {})
        return table.get(self.params.steel_grade, 0.0)

    def calculate_torque_with_grease(self) -> float:
        """Момент затяжки с учётом смазки"""
        base_torque = self.get_recommended_torque()
        k_grease = GREASE_FACTORS.get(self.params.grease_type, 1.0)
        return base_torque * k_grease

    def calculate_force_on_key(self, torque_knm: float) -> float:
        """
        Усилие на ключе: F = M / L * k_factor
        Возвращает силу в кН.
        """
        return (torque_knm / self.params.lever_arm) * self.params.k_factor

    def calculate_iv_e50_reading(self, force_kn: float) -> float:
        """
        Показание динамометра ИВЭ-50 в тоннах-сила.
        F_тс = F_кН / g, где g = 9.81 м/с²
        """
        return force_kn / 9.81

    def calculate_hydraulic_pressure(self, force_kn: float) -> float:
        """
        Давление в гидросистеме в МПа.
        P_МПа = F_Н / A_м² / 1_000_000
        Площадь поршня переводим из см² в м²: A_м² = A_см² / 10_000
        """
        piston_area_m2 = self.params.piston_area_cm2 / 10_000.0
        force_n = force_kn * 1000.0  # кН → Н
        pressure_pa = force_n / piston_area_m2
        return pressure_pa / 1_000_000.0  # Па → МПа

    def calculate_torsion_limit(self) -> float:
        """
        Предел скручивания замка по формуле сопротивления материалов:
        M_max = (π/16) * σ_y * (D - d⁴) / D
        где D, d — наружный и внутренний диаметры замка в метрах,
        σ_y — предел текучести в Па.
        Возвращает момент в кН·м.
        """
        geometry = TOOL_JOINT_GEOMETRY.get(self.params.thread_type)
        if not geometry:
            return 0.0
        D_mm, d_mm = geometry
        D_m = D_mm / 1000.0
        d_m = d_mm / 1000.0
        sigma_y_pa = STEEL_GRADES_DB.get(self.params.steel_grade, 0.0) * 1e6  # МПа → Па
        polar_section = (math.pi / 16.0) * (D_m**4 - d_m**4) / D_m
        m_max_nm = sigma_y_pa * polar_section
        return m_max_nm / 1000.0  # Н·м → кН·м

    def calculate_cable_stress(self, force_kn: float) -> float:
        """
        Напряжение в канате в МПа (для оценки запаса прочности троса).
        σ = F / A, A = π*d²/4
        """
        d_m = self.params.cable_diameter / 1000.0
        area_m2 = math.pi * d_m**2 / 4.0
        stress_pa = (force_kn * 1000.0) / area_m2
        return stress_pa / 1e6  # Па → МПа

    def get_safety_status(self, torque_knm: float, torsion_limit: float) -> str:
        """Определить статус безопасности"""
        if not self.validate_inputs():
            return "VALIDATION_ERROR"
        if torque_knm <= 0:
            return "ZERO_TORQUE"
        if torque_knm > torsion_limit:
            return "EXCEEDS_TORSION_LIMIT"
        key_data = KEY_MODELS_DB.get(self.params.key_model, {})
        max_key_torque = key_data.get("max_torque", 0)
        if torque_knm > max_key_torque:
            return "EXCEEDS_KEY_CAPACITY"
        if torque_knm < max_key_torque * 0.2:
            return "LOW_TORQUE"
        if torque_knm > max_key_torque * 0.9:
            return "HIGH_TORQUE"
        return "OPTIMAL"


# ============================================================================
# КОМПОНЕНТЫ ИНТЕРФЕЙСА
# ============================================================================

def create_umk_enhanced_panel():
    """Панель ввода параметров УМК"""
    return html.Div([
        html.H4("Расчёт усилия на ключе УМК (API RP 7G)", 
                style={"color": "#0f172a", "marginBottom": "15px"}),

        # Ряд 1: Тип контроля и модель ключа
        dbc.Row([
            dbc.Col([
                html.Label("Тип контроля натяжения:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.RadioItems(
                    id='umk-control-type',
                    options=[
                        {'label': 'Электронный (ИВЭ-50)', 'value': 'electronic'},
                        {'label': 'Гидравлический (Манометр)', 'value': 'hydraulic'}
                    ],
                    value='electronic',
                    labelStyle={'display': 'block', 'marginBottom': '5px'}
                ),
            ], width=6),
            dbc.Col([
                html.Label("Модель ключа УМК:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Dropdown(
                    id='umk-key-model',
                    options=[{"label": k, "value": k} for k in KEY_MODELS_DB.keys()],
                    value="УМК-48",
                    clearable=False
                ),
            ], width=6),
        ], className="mb-3"),

        # Ряд 2: Тип резьбы и группа прочности
        dbc.Row([
            dbc.Col([
                html.Label("Тип резьбы (API RP 7G):", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Dropdown(
                    id='umk-thread-type',
                    options=[{"label": t, "value": t} for t in API_RP_7G_TORQUE_TABLE.keys()],
                    value="NC46 (4'')",
                    clearable=False
                ),
            ], width=6),
            dbc.Col([
                html.Label("Группа прочности стали:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Dropdown(
                    id='umk-steel-grade',
                    options=[{"label": s, "value": s} for s in STEEL_GRADES_DB.keys()],
                    value="G",
                    clearable=False
                ),
            ], width=6),
        ], className="mb-3"),

        # Ряд 3: Смазка и коэффициент паспорта
        dbc.Row([
            dbc.Col([
                html.Label("Тип резьбовой смазки:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Dropdown(
                    id='umk-grease-type',
                    options=[{"label": g, "value": g} for g in GREASE_FACTORS.keys()],
                    value="Стандартная API (K=1.0)",
                    clearable=False
                ),
            ], width=6),
            dbc.Col([
                html.Label("Коэффициент из паспорта ключа (K_пасп):", 
                          style={"fontWeight": "bold", "fontSize": "13px", "color": "#dc2626"}),
                dcc.Input(
                    id='umk-passport-k-factor',
                    type='number', value=1.0, min=0.5, max=2.0, step=0.01,
                    style={"width": "100%", "padding": "8px", "border": "2px solid #dc2626"}
                ),
                html.Small("Из акта поверки ключа", style={"color": "#64748b", "fontSize": "11px"}),
            ], width=6),
        ], className="mb-3"),

        # Ряд 4: Плечо, диаметр каната, площадь поршня, ручной момент
        dbc.Row([
            dbc.Col([
                html.Label("Плечо рычага, м:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Input(id='umk-lever-arm', type='number', value=1.1,
                         min=0.1, max=5.0, step=0.05,
                         style={"width": "100%", "padding": "8px"}),
            ], width=3),
            dbc.Col([
                html.Label("Диаметр каната, мм:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Input(id='umk-cable-diam', type='number', value=12.0,
                         min=5.0, max=50.0, step=0.5,
                         style={"width": "100%", "padding": "8px"}),
            ], width=3),
            dbc.Col([
                html.Label("Площадь поршня гидроцилиндра, см²:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Input(id='umk-piston-area', type='number', value=50.0,
                         min=10.0, max=200.0, step=1.0,
                         style={"width": "100%", "padding": "8px"}),
            ], width=3),
            dbc.Col([
                html.Label("Ручной ввод момента (0 = по API), кН·м:", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Input(id='umk-manual-torque', type='number', value=0.0,
                         min=0.0, max=200.0, step=0.5,
                         style={"width": "100%", "padding": "8px"}),
            ], width=3),
        ], className="mb-3"),

        # Результаты
        html.Div(id='umk-results-enhanced', style={"marginTop": "20px"}),
    ])


def create_umk_results_display(result: dict) -> html.Div:
    """Отображение результатов расчёта"""
    status_colors = {
        "OPTIMAL": "#16a34a",
        "LOW_TORQUE": "#f59e0b",
        "HIGH_TORQUE": "#f59e0b",
        "EXCEEDS_KEY_CAPACITY": "#dc2626",
        "EXCEEDS_TORSION_LIMIT": "#dc2626",
        "VALIDATION_ERROR": "#dc2626",
        "ZERO_TORQUE": "#64748b",
    }
    status_texts = {
        "OPTIMAL": "ОПТИМАЛЬНО",
        "LOW_TORQUE": "НИЖЕ НОРМЫ",
        "HIGH_TORQUE": "ВЫШЕ НОРМЫ",
        "EXCEEDS_KEY_CAPACITY": "ПРЕВЫШЕН ЛИМИТ КЛЮЧА",
        "EXCEEDS_TORSION_LIMIT": "ПРЕВЫШЕН ПРЕДЕЛ СКРУЧИВАНИЯ ЗАМКА",
        "VALIDATION_ERROR": "ОШИБКА ВАЛИДАЦИИ",
        "ZERO_TORQUE": "МОМЕНТ НЕ ЗАДАН",
    }

    color = status_colors.get(result["status"], "#64748b")
    status_text = status_texts.get(result["status"], "НЕИЗВЕСТНО")

    # Формирование предупреждений
    warnings = []
    if result["k_factor"] != 1.0:
        warnings.append(html.Div(
            f"Применён коэффициент из паспорта: {result['k_factor']:.2f}",
            style={"color": "#F59E0B", "fontSize": "12px", "marginTop": "5px"}
        ))
    if result["cable_stress_mpa"] > 500:
        warnings.append(html.Div(
            f"Напряжение в канате {result['cable_stress_mpa']:.0f} МПа — проверить запас прочности троса!",
            style={"color": "#dc2626", "fontSize": "12px", "marginTop": "5px"}
        ))
    if result["validation_errors"]:
        for err in result["validation_errors"]:
            warnings.append(html.Div(
                f"Ошибка: {err}",
                style={"color": "#dc2626", "fontSize": "12px", "marginTop": "5px"}
            ))

    return html.Div([
        # Главный индикатор
        html.Div(style={
            "backgroundColor": "#111827", "padding": "20px", "borderRadius": "8px",
            "textAlign": "center", "border": f"3px solid {color}"
        }, children=[
            html.Div(result["metric_title"], 
                    style={"color": "#9CA3AF", "fontSize": "13px", "marginBottom": "10px"}),
            html.Div(f"{result['display_value']:.2f} {result['unit']}", 
                    style={"color": color, "fontSize": "36px", "fontWeight": "bold"}),
            html.Div(f"Статус: {status_text}", 
                    style={"color": color, "fontSize": "14px", "marginTop": "10px"}),
        ]),

        # Предупреждения
        *warnings if warnings else [html.Div("")],

        # Детализация
        html.Div(style={"marginTop": "15px", "padding": "15px", "backgroundColor": "#F3F4F6", "borderRadius": "6px"}, children=[
            html.H6("Детализация расчёта:", style={"marginBottom": "10px"}),
            html.P(f"Рекомендуемый момент (API RP 7G): {result['base_torque']:.2f} кН·м", style={"margin": "5px 0"}),
            html.P(f"Момент с учётом смазки: {result['torque_with_grease']:.2f} кН·м", style={"margin": "5px 0"}),
            html.P(f"Фактическое усилие на ключе: {result['force_kn']:.2f} кН", style={"margin": "5px 0"}),
            html.P(f"Плечо рычага: {result['lever_arm']} м", style={"margin": "5px 0"}),
            html.P(f"Предел скручивания замка: {result['torsion_limit']:.2f} кН·м", style={"margin": "5px 0"}),
            html.P(f"Напряжение в канате: {result['cable_stress_mpa']:.1f} МПа", style={"margin": "5px 0"}),
        ]),
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def umk_enhanced_callbacks(app, data_bridge):
    """Регистрация callback'ов для модуля УМК"""

    @app.callback(
        Output('umk-results-enhanced', 'children'),
        [Input('umk-control-type', 'value'),
         Input('umk-key-model', 'value'),
         Input('umk-thread-type', 'value'),
         Input('umk-steel-grade', 'value'),
         Input('umk-grease-type', 'value'),
         Input('umk-passport-k-factor', 'value'),
         Input('umk-lever-arm', 'value'),
         Input('umk-cable-diam', 'value'),
         Input('umk-piston-area', 'value'),
         Input('umk-manual-torque', 'value')]
    )
    def update_umk_results(control_type, key_model, thread_type, steel_grade,
                           grease_type, k_factor, lever_arm, cable_diam,
                           piston_area, manual_torque):
        # Защита от None
        if k_factor is None: k_factor = 1.0
        if lever_arm is None or lever_arm <= 0: lever_arm = 1.1
        if cable_diam is None: cable_diam = 12.0
        if piston_area is None: piston_area = 50.0
        if manual_torque is None: manual_torque = 0.0

        params = UMKParameters(
            key_model=key_model,
            thread_type=thread_type,
            steel_grade=steel_grade,
            grease_type=grease_type,
            lever_arm=lever_arm,
            k_factor=k_factor,
            cable_diameter=cable_diam,
            piston_area_cm2=piston_area,
            target_torque_override=manual_torque,
        )

        calc = UMKCalculator(params)
        validation_errors = calc.validation_errors if not calc.validate_inputs() else []

        # Расчёты
        base_torque = calc.get_recommended_torque()
        torque_with_grease = calc.calculate_torque_with_grease()
        force_kn = calc.calculate_force_on_key(torque_with_grease)
        torsion_limit = calc.calculate_torsion_limit()
        cable_stress = calc.calculate_cable_stress(force_kn)
        status = calc.get_safety_status(torque_with_grease, torsion_limit)

        # Выбор метрики в зависимости от типа контроля
        if control_type == 'electronic':
            display_value = calc.calculate_iv_e50_reading(force_kn)
            unit = "тс (тонн-сила)"
            metric_title = "ЦЕЛЕВОЕ УСИЛИЕ НА ИВЭ-50"
        else:
            display_value = calc.calculate_hydraulic_pressure(force_kn)
            unit = "МПа"
            metric_title = "ЦЕЛЕВОЕ ДАВЛЕНИЕ НА МАНОМЕТРЕ"

        result = {
            "display_value": display_value,
            "unit": unit,
            "metric_title": metric_title,
            "status": status,
            "base_torque": base_torque,
            "torque_with_grease": torque_with_grease,
            "force_kn": force_kn,
            "torsion_limit": torsion_limit,
            "cable_stress_mpa": cable_stress,
            "k_factor": k_factor,
            "lever_arm": lever_arm,
            "validation_errors": validation_errors,
        }

        return create_umk_results_display(result)
