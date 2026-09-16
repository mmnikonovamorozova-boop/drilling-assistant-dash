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
        sigma_y_pa = STEEL_GRADES_DB.get(self.params.steel_grade, 0.0) * 1e6 
