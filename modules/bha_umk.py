"""
МОДУЛЬ РАСЧЕТА УМК (УПРАВЛЕНИЕ МОМЕНТОМ ЗАТЯЖКИ КЛЮЧА)
Расчет целевого усилия на ключе для затяжки резьбовых соединений КНБК.
Соответствие API RP 7G и СТО ИНТИ S.QS.8.
"""
import math
import logging
from dataclasses import dataclass
from typing import Tuple
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# КЛАСС ДЛЯ РАСЧЕТОВ УМК (Вынесенная математика)
# ============================================================================

@dataclass
class UMKParameters:
    """Параметры для расчета УМК"""
    key_model: str  # Модель ключа УМК
    lever_arm: float  # Плечо рычага, м
    grease_type: str  # Тип смазки
    pipe_steel: str  # Группа прочности стали
    pipe_od: float  # Наружный диаметр трубы, мм
    thread_type: str  # Тип резьбы
    target_torque: float = 0.0  # Целевой момент, кН·м
    force_kn: float = 0.0  # Усилие на ключе, кН
    safety_status: str = "UNKNOWN"  # Статус безопасности

# База данных моделей ключей УМК (паспортные данные)
KEY_MODELS_DB = {
    "УМК-10/1": {"max_torque": 10.0, "lever_arm": 0.615, "weight": 45},
    "УМК-35": {"max_torque": 35.0, "lever_arm": 0.900, "weight": 120},
    "УМК-48": {"max_torque": 48.0, "lever_arm": 1.100, "weight": 180},
    "УМК-75": {"max_torque": 75.0, "lever_arm": 1.400, "weight": 280},
    "УМК-90": {"max_torque": 90.0, "lever_arm": 1.400, "weight": 320},
}

# Коэффициенты трения для разных типов смазки (СТО ИНТИ S.QS.8)
GREASE_FACTORS = {
    "Стандартная API (K=1.0)": 1.0,
    "Графитовая (K=1.15)": 1.15,
    "Тефлоновая (K=0.85)": 0.85,
    "Медная специальная (K=1.3)": 1.3,
}

# Группы прочности стали (API Spec 5DP)
STEEL_GRADES = {
    "D (379 МПа)": {"yield": 379, "tensile": 621},
    "E (517 МПа)": {"yield": 517, "tensile": 758},
    "X (689 МПа)": {"yield": 689, "tensile": 896},
    "G (724 МПа)": {"yield": 724, "tensile": 931},
    "S (931 МПа)": {"yield": 931, "tensile": 1138},
}

# Типы резьбы и рекомендуемые моменты затяжки (API RP 7G)
THREAD_TYPES = {
    "NC26 (2-3/8'')": {"nominal_torque": 15.5, "makeup_turns": "3-4"},
    "NC31 (2-7/8'')": {"nominal_torque": 22.0, "makeup_turns": "3-4"},
    "NC38 (3-1/2'')": {"nominal_torque": 32.5, "makeup_turns": "3-4"},
    "NC46 (4'')": {"nominal_torque": 52.0, "makeup_turns": "3-4"},
    "NC50 (4-1/2'')": {"nominal_torque": 72.0, "makeup_turns": "3-4"},
    "6-5/8 FH": {"nominal_torque": 95.0, "makeup_turns": "3-4"},
}


class UMKCalculator:
    """Калькулятор момента затяжки УМК"""
    
    def __init__(self, params: UMKParameters):
        self.params = params
        self.validation_errors = []
    
    def validate_inputs(self) -> bool:
        """Валидация входных данных"""
        self.validation_errors = []
        
        if self.params.lever_arm <= 0 or self.params.lever_arm > 5.0:
            self.validation_errors.append("Плечо рычага должно быть в диапазоне 0.1 - 5.0 м")
        
        if self.params.pipe_od <= 0 or self.params.pipe_od > 500:
            self.validation_errors.append("Наружный диаметр трубы должен быть в диапазоне 50 - 500 мм")
        
        if self.params.target_torque < 0:
            self.validation_errors.append("Целевой момент не может быть отрицательным")
        
        if self.validation_errors:
            logger.warning(f"Validation errors: {self.validation_errors}")
            return False
        
        return True
    
    def calculate_force(self) -> Tuple[float, str]:
        """
        Расчет усилия на ключе УМК.
        
        Формула: F = M / L, где
        F - усилие на ключе, кН
        M - целевой момент затяжки, кН·м
        L - плечо рычага, м
        
        Возвращает: (усилие_кН, статус)
        """
        try:
            if not self.validate_inputs():
                return 0.0, "VALIDATION_ERROR"
            
            # Базовый расчет усилия
            force_kn = self.params.target_torque / self.params.lever_arm
            
            # Проверка на превышение максимального момента ключа
            key_model_data = KEY_MODELS_DB.get(self.params.key_model)
            if key_model_data:
                max_torque = key_model_data["max_torque"]
                if self.params.target_torque > max_torque:
                    return force_kn, "EXCEEDS_KEY_CAPACITY"
            
            # Проверка на предел текучести стали
            steel_data = STEEL_GRADES.get(self.params.pipe_steel)
            if steel_data:
                # Упрощенный расчет максимального допустимого момента
                # M_max = (yield_strength * 0.6) * (pipe_od / 1000) * 0.001
                max_allowed_torque = (steel_data["yield"] * 0.6) * (self.params.pipe_od / 1000) * 0.001
                if self.params.target_torque > max_allowed_torque:
                    return force_kn, "EXCEEDS_STEEL_LIMIT"
            
            # Определение статуса безопасности
            if self.params.target_torque < key_model_data["max_torque"] * 0.3:
                status = "LOW_TORQUE"  # Слишком малый момент
            elif self.params.target_torque > key_model_data["max_torque"] * 0.9:
                status = "HIGH_TORQUE"  # Близко к пределу
            else:
                status = "OPTIMAL"  # Оптимальная зона
            
            return force_kn, status
        
        except ZeroDivisionError as e:
            logger.error(f"Division by zero in force calculation: {e}")
            return 0.0, "CALCULATION_ERROR"
        except Exception
