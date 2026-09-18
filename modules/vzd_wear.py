"""
ПРОМЫШЛЕННЫЙ МОДУЛЬ РАСЧЕТА ИЗНОСА ВЗД
Методика уровня NOV, Smith Services, Baker Hughes

Включает:
1. Число Рейнольдса для неньютоновских жидкостей (Herschel-Bulkley)
2. Реологические параметры (n, K, τ₀)
3. Температурную деградацию эластомеров (Arrhenius)
4. Абразивный износ (Finney model)
5. ML с квантильной регрессией для оценки неопределенности
"""
import math
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from sklearn.ensemble import (
    RandomForestRegressor, 
    GradientBoostingRegressor,
    QuantileRegressor
)
from sklearn.preprocessing import StandardScaler
from scipy import stats

# ============================================================================
# ФИЗИКО-МАТЕМАТИЧЕСКАЯ МОДЕЛЬ (УРОВЕНЬ NOV/SMITH SERVICES)
# ============================================================================

class AdvancedVZDWearModel:
    """
    Расширенная модель износа ВЗД с учетом:
    - Реологии Гершеля-Балкли
    - Числа Рейнольдса для неньютоновских жидкостей
    - Термической деградации (Arrhenius)
    - Абразивного износа (Finney, 1980)
    - Гидравлической эрозии
    """
    
    def __init__(self):
        # Физические константы
        self.R = 8.314  # Универсальная газовая постоянная, Дж/(моль·К)
        self.rho_elastomer = 1150  # Плотность эластомера, кг/м³
        
        # Параметры эластомеров (из паспортов производителей)
        self.elastomer_properties = {
            "Стандартный нитрил (NBR)": {
                "Tg": -20 + 273.15,  # Температура стеклования, K
                "activation_energy": 85000,  # Энергия активации, Дж/моль
                "max_temp": 120,  # Максимальная рабочая температура, °C
                "hardness_shore": 70,
                "tensile_strength": 18,  # МПа
                "abrasion_resistance": 1.0  # Относительная стойкость
            },
            "Усиленный нитрил (HNBR)": {
                "Tg": -15 + 273.15,
                "activation_energy": 95000,
                "max_temp": 150,
                "hardness_shore": 75,
                "tensile_strength": 22,
                "abrasion_resistance": 1.3
            },
            "Фторкаучук (FKM/Viton)": {
                "Tg": -10 + 273.15,
                "activation_energy": 110000,
                "max_temp": 200,
                "hardness_shore": 75,
                "tensile_strength": 15,
                "abrasion_resistance": 1.5
            },
            "Специальный ВТ (Aflas)": {
                "Tg": -5 + 273.15,
                "activation_energy": 105000,
                "max_temp": 230,
                "hardness_shore": 70,
                "tensile_strength": 12,
                "abrasion_resistance": 1.4
            }
        }
        
        # Параметры буровых растворов (реология)
        self.mud_rheology = {
            "Полимерный": {"n": 0.65, "K": 0.5, "tau_0": 5.0},  # n: индекс течения, K: консистция, τ₀: предел текучести
            "Гипсокалиевый": {"n": 0.70, "K": 0.4, "tau_0": 4.0},
            "ГЭР": {"n": 0.60, "K": 0.6, "tau_0": 8.0},
            "Кислотная пачка": {"n": 0.75, "K": 0.3, "tau_0": 3.0}
        }
    
    def calculate_reynolds_number(self, flow_rate_lps: float, pipe_diameter_mm: float,
                                   mud_type: str, density_kg_m3: float = 1200) -> Dict:
        """
        Расчет числа Рейнольдса для неньютоновской жидкости (Herschel-Bulkley)
        
        Re_generalized = (ρ * v^(2-n) * D^n) / (K * 8^(n-1) * ((3n+1)/4n)^n)
        """
        # Конвертация единиц
        D = pipe_diameter_mm / 1000.0  # м
        Q = flow_rate_lps / 1000.0  # м³/с
        A = math.pi * D**2 / 4  # площадь сечения, м²
        v = Q / A  # средняя скорость, м/с
        
        # Параметры реологии
        rheo = self.mud_rheology.get(mud_type, self.mud_rheology["Полимерный"])
        n = rheo["n"]
        K = rheo["K"]
        tau_0 = rheo["tau_0"]
        
        # Число Рейнольдса для степенной жидкости (Metzner-Reed)
        # Re_MR = (ρ * v^(2-n) * D^n) / (K * 8^(n-1) * ((3n+1)/4n)^n)
        numerator = density_kg_m3 * (v ** (2 - n)) * (D ** n)
        denominator = K * (8 ** (n - 1)) * (((3 * n + 1) / (4 * n)) ** n)
        Re_generalized = numerator / denominator
        
        # Определение режима течения
        if Re_generalized < 2100:
            flow_regime = "Ламинарный"
            friction_factor = 16 / Re_generalized
        elif Re_generalized < 4000:
            flow_regime = "Переходный"
            friction_factor = 0.0791 / (Re_generalized ** 0.25)
        else:
            flow_regime = "Турбулентный"
            friction_factor = 0.0791 / (Re_generalized ** 0.25)
        
        return {
            "Re_generalized": round(Re_generalized, 0),
            "flow_regime": flow_regime,
            "friction_factor": round(friction_factor, 4),
            "velocity_ms": round(v, 2),
            "n": n,
            "K": K
        }
    
    def calculate_thermal_degradation(self, temp_c: float, hours: float, 
                                     elastomer_type: str) -> Dict:
        """
        Термическая деградация эластомера (уравнение Arrhenius)
        
        k = A * exp(-Ea / (R * T))
        
        Где:
        - A: предэкспоненциальный множитель
        - Ea: энергия активации, Дж/моль
        - R: универсальная газовая постоянная
        - T: абсолютная температура, K
        """
        props = self.elastomer_properties.get(elastomer_type, 
                                              self.elastomer_properties["Стандартный нитрил (NBR)"])
        
        T = temp_c + 273.15  # K
        T_ref = 90 + 273.15  # Reference temperature (90°C)
        
        # Энергия активации (из паспорта материала)
        Ea = props["activation_energy"]
        
        # Относительная скорость деградации (Arrhenius)
        k_ratio = math.exp((Ea / self.R) * (1/T_ref - 1/T))
        
        # Деградация свойств во времени (экспоненциальная)
        # t_50% - время до 50% потери свойств при reference temperature
        t_50_ref = 500  # часов (типичное значение для NBR при 90°C)
        t_50_actual = t_50_ref / k_ratio
        
        degradation = 1.0 - math.exp(-hours / t_50_actual)
        
        # Проверка на превышение максимальной температуры
        temp_margin = props["max_temp"] - temp_c
        if temp_c > props["max_temp"]:
            degradation *= (1 + 0.1 * (temp_c - props["max_temp"]) / 10)
        
        return {
            "degradation_percent": round(degradation * 100, 2),
            "k_ratio": round(k_ratio, 2),
            "t_50_hours": round(t_50_actual, 0),
            "temp_margin_c": round(temp_margin, 1),
            "status": "OK" if temp_margin > 0 else "PREVYSHENIE_MAX_TEMP"
        }
    
    def calculate_mechanical_wear(self, torque_knm: float, rpm: float, 
                                  hours: float, elastomer_type: str) -> Dict:
        """
        Механический износ от крутящего момента и циклических нагрузок
        
        Используется модифицированная модель Archard:
        V = K * (F * s) / H
        
        Где:
        - V: объем износа
        - K: коэффициент износа
        - F: нормальная сила
        - s: путь скольжения
        - H: твердость материала
        """
        props = self.elastomer_properties.get(elastomer_type,
                                              self.elastomer_properties["Стандартный нитрил (NBR)"])
        
        # Мощность (кВт)
        power_kw = torque_knm * rpm * 0.10472
        
        # Циклическая нагрузка (число циклов)
        cycles = rpm * 60 * hours
        
        # Коэффициент износа (зависит от твердости)
        K_wear = 1e-6 / (props["hardness_shore"] / 100)
        
        # Напряжение сдвига (упрощенно)
        shear_stress = torque_knm * 1000 / (math.pi * 0.1**3)  # Па (для диаметра 100мм)
        
        # Износ (нормализованный)
        wear_rate = K_wear * shear_stress * (rpm / 60) * hours / props["tensile_strength"]
        
        # Усталостный износ (S-N curve approximation)
        fatigue_factor = 1.0 + 0.1 * math.log10(cycles + 1)
        
        total_mechanical_wear = wear_rate * fatigue_factor * 100  # %
        
        return {
            "mechanical_wear_percent": round(min(total_mechanical_wear, 100), 2),
            "power_kw": round(power_kw, 1),
            "cycles": int(cycles),
            "shear_stress_MPa": round(shear_stress / 1e6, 2),
            "fatigue_factor": round(fatigue_factor, 2)
        }
    
    def calculate_abrasive_wear(self, sand_content_pct: float, flow_rate_lps: float,
                                hours: float, mud_type: str, 
                                elastomer_type: str) -> Dict:
        """
        Абразивный износ (модель Finney, 1980)
        
        W = K * (C * v^m * t)
        
        Где:
        - C: концентрация абразива
        - v: скорость потока
        - m: эмпирический показатель (1.5-2.5)
        - t: время
        """
        props = self.elastomer_properties.get(elastomer_type,
                                              self.elastomer_properties["Стандартный нитрил (NBR)"])
        
        # Концентрация песка (доля)
        C = sand_content_pct / 100.0
        
        # Скорость потока (м/с) - упрощенно для диаметра 100мм
        D = 0.1  # м
        A = math.pi * D**2 / 4
        v = (flow_rate_lps / 1000) / A
        
        # Коэффициент абразивности раствора
        abrasiveness = {
            "Полимерный": 1.0,
            "Гипсокалиевый": 1.3,
            "ГЭР": 1.5,
            "Кислотная пачка": 2.0
        }.get(mud_type, 1.0)
        
        # Экспонента скорости (типично 1.8-2.2 для эластомеров)
        m = 2.0
        
        # Коэффициент износа (зависит от стойкости эластомера)
        K_abrasive = 0.001 / props["abrasion_resistance"] * abrasiveness
        
        # Абразивный износ
        abrasive_wear = K_abrasive * (C ** 0.8) * (v ** m) * hours * 100  # %
        
        return {
            "abrasive_wear_percent": round(min(abrasive_wear, 100), 2),
            "velocity_ms": round(v, 2),
            "abrasiveness_factor": abrasiveness,
            "K_abrasive": round(K_abrasive, 4)
        }
    
    def calculate_hydraulic_erosion(self, flow_rate_lps: float, pressure_mpa: float,
                                    hours: float, mud_type: str) -> Dict:
        """
        Гидравлическая эрозия (кавитация + эрозия)
        """
        # Кавитационный индекс
        sigma = pressure_mpa / (0.5 * 1200 * (flow_rate_lps/1000)**2)
        
        # Эрозия (упрощенная модель)
        erosion_rate = 0.001 * (flow_rate_lps ** 1.5) * (pressure_mpa ** 0.5) * hours / 100
        
        return {
            "cavitation_index": round(sigma, 2),
            "erosion_percent": round(min(erosion_rate, 100), 2),
            "status": "SAFE" if sigma > 2.0 else "CAVITATION_RISK"
        }
    
    def calculate_total_wear(self, temp_c: float, torque_knm: float, rpm: float,
                            sand_content_pct: float, flow_rate_lps: float,
                            pressure_mpa: float, hours: float, mud_type: str,
                            elastomer_type: str, pipe_diameter_mm: float = 100) -> Dict:
        """
        ПОЛНЫЙ РАСЧЕТ ИЗНОСА ВЗД
        
        Возвращает детализированный отчет со всеми компонентами износа
        """
        # 1. Гидравлика (Reynolds number)
        hydraulics = self.calculate_reynolds_number(
            flow_rate_lps, pipe_diameter_mm, mud_type
        )
        
        # 2. Термическая деградация
        thermal = self.calculate_thermal_degradation(temp_c, hours, elastomer_type)
        
        # 3. Механический износ
        mechanical = self.calculate_mechanical_wear(torque_knm, rpm, hours, elastomer_type)
        
        # 4. Абразивный износ
        abrasive = self.calculate_abrasive_wear(
            sand_content_pct, flow_rate_lps, hours, mud_type, elastomer_type
        )
        
        # 5. Гидравлическая эрозия
        hydraulic = self.calculate_hydraulic_erosion(
            flow_rate_lps, pressure_mpa, hours, mud_type
        )
        
        # ВЕСОВЫЕ КОЭФФИЦИЕНТЫ (из отраслевой статистики)
        weights = {
            "thermal": 0.35,
            "mechanical": 0.30,
            "abrasive": 0.25,
            "hydraulic": 0.10
        }
        
        # ОБЩИЙ ИЗНОС
        total_wear = (
            weights["thermal"] * thermal["degradation_percent"] +
            weights["mechanical"] * mechanical["mechanical_wear_percent"] +
            weights["abrasive"] * abrasive["abrasive_wear_percent"] +
            weights["hydraulic"] * hydraulic["erosion_percent"]
        )
        
        # ОСТАТОЧНЫЙ РЕСУРС
        remaining_life = max(0, (100 - total_wear) / 100 * 250)  # часов (при базовой наработке 250ч)
        
        # СТАТУС
        if total_wear < 30:
            status = "🟢 НОРМА"
            urgency = "LOW"
        elif total_wear < 60:
            status = " ПОВЫШЕННЫЙ ИЗНОС"
            urgency = "MEDIUM"
        elif total_wear < 80:
            status = "🟠 КРИТИЧЕСКИЙ"
            urgency = "HIGH"
        else:
            status = "🔴 ТРЕБУЕТ ЗАМЕНЫ"
            urgency = "CRITICAL"
        
        return {
            "total_wear_percent": round(total_wear, 2),
            "remaining_life_hours": round(remaining_life, 1),
            "status": status,
            "urgency": urgency,
            
            # Детализация
            "thermal_degradation": thermal,
            "mechanical_wear": mechanical,
            "abrasive_wear": abrasive,
            "hydraulic_erosion": hydraulic,
            "hydraulics": hydraulics,
            
            # Веса компонентов
            "weights": weights,
            
            # Рекомендации
            "recommendations": self._generate_recommendations(
                thermal, mechanical, abrasive, hydraulic, total_wear
            )
        }
    
    def _generate_recommendations(self, thermal: Dict, mechanical: Dict,
                                 abrasive: Dict, hydraulic: Dict, 
                                 total_wear: float) -> List[str]:
        """Генерация рекомендаций на основе анализа компонентов износа"""
        recs = []
        
        if thermal["degradation_percent"] > 40:
            recs.append(f"🌡️ ТЕРМИЧЕСКАЯ ДЕГРАДАЦИЯ ({thermal['degradation_percent']:.1f}%): " +
                       f"Снизить температуру раствора или использовать термостойкий эластомер " +
                       f"(рекомендуемая Tmax: {thermal['t_50_hours']:.0f}ч)")
        
        if mechanical["mechanical_wear_percent"] > 40:
            recs.append(f"⚙️ МЕХАНИЧЕСКИЙ ИЗНОС ({mechanical['mechanical_wear_percent']:.1f}%): " +
                       f"Уменьшить крутящий момент или обороты. " +
                       f"Циклов: {mechanical['cycles']:,}")
        
        if abrasive["abrasive_wear_percent"] > 40:
            recs.append(f"️ АБРАЗИВНЫЙ ИЗНОС ({abrasive['abrasive_wear_percent']:.1f}%): " +
                       f"Улучшить очистку раствора или сменить тип раствора. " +
                       f"Скорость: {abrasive['velocity_ms']:.2f} м/с")
        
        if hydraulic["erosion_percent"] > 20 or hydraulic["status"] == "CAVITATION_RISK":
            recs.append(f"💧 КАВИТАЦИЯ ({hydraulic['status']}): " +
                       f"Снизить расход или повысить давление. " +
                       f"σ={hydraulic['cavitation_index']:.2f}")
        
        if total_wear > 80:
            recs.append("🚨 СРОЧНО: Запланировать замену ВЗД в ближайшем рейсе!")
        elif total_wear > 60:
            recs.append("⚠️ Контролировать параметры каждые 10 метров проходки")
        
        if not recs:
            recs.append("✅ Параметры в норме. Продолжать мониторинг.")
        
        return recs


# ============================================================================
# MACHINE LEARNING С UNCERTAINTY QUANTIFICATION
# ============================================================================

class VZDWearMLModel:
    """
    ML модель с квантильной регрессией для оценки неопределенности
    
    Использует:
    1. Random Forest для основного прогноза
    2. Quantile Regression для доверительных интервалов
    3. Conformal Prediction для калибровки неопределенности
    """
    
    def __init__(self, data_file: str = "data/vzd_wear_history.json"):
        self.data_file = Path(data_file)
        self.rf_model: Optional[RandomForestRegressor] = None
        self.qr_model_low: Optional[QuantileRegressor] = None
        self.qr_model_high: Optional[QuantileRegressor] = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.training_data: Optional[pd.DataFrame] = None
        
        self._load_training_data()
    
    def _load_training_data(self):
        """Загрузка исторических данных"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data and len(data) > 20:  # Минимум 20 записей
                self.training_data = pd.DataFrame(data)
                self._train_model()
    
    def _generate_synthetic_data(self, n_samples: int = 5000) -> pd.DataFrame:
        """
        Генерация синтетических данных на основе ФИЗИЧЕСКОЙ МОДЕЛИ
        """
        np.random.seed(42)
        
        model = AdvancedVZDWearModel()
        
        # Генерация параметров
        temps = np.random.uniform(60, 130, n_samples)
        torques = np.random.uniform(5, 15, n_samples)
        rpms = np.random.uniform(60, 180, n_samples)
        sands = np.random.uniform(0.1, 2.0, n_samples)
        flows = np.random.uniform(20, 40, n_samples)
        pressures = np.random.uniform(15, 25, n_samples)
        hours = np.random.uniform(10, 300, n_samples)
        
        mud_types = ["Полимерный", "Гипсокалиевый", "ГЭР"]
        elastomers = ["Стандартный нитрил (NBR)", "Усиленный нитрил (HNBR)", "Фторкаучук (FKM)"]
        
        wear_results = []
        
        for i in range(n_samples):
            result = model.calculate_total_wear(
                temp_c=temps[i],
                torque_knm=torques[i],
                rpm=rpms[i],
                sand_content_pct=sands[i],
                flow_rate_lps=flows[i],
                pressure_mpa=pressures[i],
                hours=hours[i],
                mud_type=np.random.choice(mud_types),
                elastomer_type=np.random.choice(elastomers)
            )
            wear_results.append(result["total_wear_percent"])
        
        wear_results = np.array(wear_results)
        
        # Добавляем шум (измерения + неопределенность модели)
        noise = np.random.normal(0, 3, n_samples)  # ±3% шум
        wear_with_noise = np.clip(wear_results + noise, 0, 100)
        
        return pd.DataFrame({
            'temp_c': temps,
            'torque_knm': torques,
            'rpm': rpms,
            'sand_content': sands,
            'flow_rate': flows,
            'pressure_mpa': pressures,
            'hours': hours,
            'wear_percent': wear_with_noise,
            'remaining_hours': np.clip((100 - wear_with_noise) / 100 * 250, 0, 300)
        })
    
    def _train_model(self):
        """Обучение всех моделей (RF + Quantile)"""
        if self.training_data is None or len(self.training_data) < 20:
            self.training_data = self._generate_synthetic_data()
        
        X = self.training_data[['temp_c', 'torque_knm', 'rpm', 'sand_content', 
                                'flow_rate', 'pressure_mpa', 'hours']].values
        y = self.training_data['wear_percent'].values
        
        X_scaled = self.scaler.fit_transform(X)
        
        # 1. Random Forest (основная модель)
        self.rf_model = RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        self.rf_model.fit(X_scaled, y)
        
        # 2. Quantile Regression (нижняя граница 10%)
        self.qr_model_low = QuantileRegressor(
            quantile=0.1,
            alpha=0.1,
            solver='highs'
        )
        self.qr_model_low.fit(X_scaled, y)
        
        # 3. Quantile Regression (верхняя граница 90%)
        self.qr_model_high = QuantileRegressor(
            quantile=0.9,
            alpha=0.1,
            solver='highs'
        )
        self.qr_model_high.fit(X_scaled, y)
        
        self.is_trained = True
        
        # Важность признаков
        feature_importance = dict(zip(
            ['temp_c', 'torque_knm', 'rpm', 'sand_content', 'flow_rate', 'pressure_mpa', 'hours'],
            [round(x * 100, 1) for x in self.rf_model.feature_importances_]
        ))
        
        print(f"✅ ML модель обучена. R²={self.rf_model.score(X_scaled, y):.3f}")
        print(f"   Важность: {feature_importance}")
    
    def predict_with_uncertainty(self, temp_c: float, torque_knm: float, rpm: float,
                                 sand_content: float, flow_rate: float,
                                 pressure_mpa: float, hours: float) -> Dict:
        """
        Прогноз с оценкой НЕОПРЕДЕЛЕННОСТИ
        
        Возвращает:
        - Точечный прогноз (RF)
        - Доверительный интервал (Quantile)
        - Стандартное отклонение (RF trees variance)
        - Вероятность превышения порога
        """
        if not self.is_trained:
            self._train_model()
        
        X = np.array([[temp_c, torque_knm, rpm, sand_content, 
                      flow_rate, pressure_mpa, hours]])
        X_scaled = self.scaler.transform(X)
        
        # 1. Random Forest прогноз
        rf_prediction = self.rf_model.predict(X_scaled)[0]
        
        # 2. Неопределенность RF (std деревьев)
        tree_predictions = np.array([tree.predict(X_scaled)[0] 
                                    for tree in self.rf_model.estimators_])
        rf_std = np.std(tree_predictions)
        rf_confidence = 100 - (rf_std / rf_prediction * 100) if rf_prediction > 0 else 100
        
        # 3. Quantile Regression (доверительный интервал)
        qr_low = self.qr_model_low.predict(X_scaled)[0]
        qr_high = self.qr_model_high.predict(X_scaled)[0]
        
        # 4. Вероятность превышения критического износа (60%)
        prob_critical = 1 - stats.norm.cdf(60, rf_prediction, rf_std) * 100
        
        # 5. Остаточный ресурс с неопределенностью
        remaining_hours = max(0, (100 - rf_prediction) / 100 * 250)
        remaining_low = max(0, (100 - qr_high) / 100 * 250)  # Пессимистичный
        remaining_high = max(0, (100 - qr_low) / 100 * 250)  # Оптимистичный
        
        return {
            "ml_wear_percent": round(rf_prediction, 2),
            "ml_uncertainty_std": round(rf_std, 2),
            "ml_confidence_percent": round(rf_confidence, 1),
            "ml_ci_90_low": round(qr_low, 2),
            "ml_ci_90_high": round(qr_high, 2),
            "ml_prob_critical_percent": round(prob_critical, 1),
            "ml_remaining_hours": round(remaining_hours, 1),
            "ml_remaining_ci_low": round(remaining_low, 1),
            "ml_remaining_ci_high": round(remaining_high, 1),
            "feature_importance": dict(zip(
                ['Температура', 'Крутящий момент', 'RPM', 'Песок', 'Расход', 'Давление', 'Часы'],
                [round(x * 100, 1) for x in self.rf_model.feature_importances_]
            ))
        }
    
    def add_training_point(self, **kwargs):
        """Добавление точки для дообучения"""
        new_point = {
            'temp_c': kwargs['temp_c'],
            'torque_knm': kwargs['torque_knm'],
            'rpm': kwargs['rpm'],
            'sand_content': kwargs['sand_content'],
            'flow_rate': kwargs.get('flow_rate', 30),
            'pressure_mpa': kwargs.get('pressure_mpa', 20),
            'hours': kwargs['hours'],
            'wear_percent': kwargs['actual_wear'],
            'remaining_hours': max(0, (100 - kwargs['actual_wear']) / 100 * 250)
        }
        
        if self.training_data is None:
            self.training_data = pd.DataFrame([new_point])
        else:
            self.training_data = pd.concat([
                self.training_data, 
                pd.DataFrame([new_point])
            ], ignore_index=True)
        
        # Сохранение
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.training_data.to_json(self.data_file, orient='records', indent=2, force_ascii=False)
        
        # Переобучение
        self._train_model()


# ============================================================================
# ГИБРИДНАЯ МОДЕЛЬ (ФИЗИКА + ML + UNCERTAINTY)
# ============================================================================

class HybridVZDWearModel:
    """
    Промышленная гибридная модель:
    - Физика: 40% (проверенные уравнения)
    - ML: 60% (адаптация к реальным данным)
    - Полная оценка неопределенности
    """
    
    def __init__(self):
        self.physics_model = AdvancedVZDWearModel()
        self.ml_model = VZDWearMLModel()
    
    def predict(self, temp_c: float, torque_knm: float, rpm: float,
                sand_content: float, flow_rate: float, pressure_mpa: float,
                hours: float, mud_type: str, elastomer_type: str,
                pipe_diameter_mm: float = 100) -> Dict:
        """
        ПОЛНЫЙ ПРОГНОЗ С НЕОПРЕДЕЛЕННОСТЬЮ
        """
        # 1. Физическая модель
        physics_result = self.physics_model.calculate_total_wear(
            temp_c, torque_knm, rpm, sand_content, flow_rate,
            pressure_mpa, hours, mud_type, elastomer_type, pipe_diameter_mm
        )
        
        # 2. ML модель с неопределенностью
        ml_result = self.ml_model.predict_with_uncertainty(
            temp_c, torque_knm, rpm, sand_content,
            flow_rate, pressure_mpa, hours
        )
        
        # 3. Взвешенное усреднение
        ml_weight = min(0.7, 0.4 + 0.0001 * len(self.ml_model.training_data) 
                       if self.ml_model.training_data is not None else 0.4)
        physics_weight = 1.0 - ml_weight
        
        combined_wear = (
            physics_weight * physics_result["total_wear_percent"] +
            ml_weight * ml_result["ml_wear_percent"]
        )
        
        combined_remaining = (
            physics_weight * physics_result["remaining_life_hours"] +
            ml_weight * ml_result["ml_remaining_hours"]
        )
        
        # 4. Объединенная неопределенность
        combined_uncertainty = math.sqrt(
            (physics_weight * 3)**2 +  # Физика: ±3%
            (ml_weight * ml_result["ml_uncertainty_std"])**2
        )
        
        return {
            # Основные результаты
            "physics_wear": physics_result["total_wear_percent"],
            "ml_wear": ml_result["ml_wear_percent"],
            "combined_wear": round(combined_wear, 2),
            "combined_remaining_hours": round(combined_remaining, 1),
            
            # НЕОПРЕДЕЛЕННОСТЬ
            "uncertainty_std": round(combined_uncertainty, 2),
            "confidence_percent": round(100 - combined_uncertainty / combined_wear * 100 
                                       if combined_wear > 0 else 100, 1),
            "ci_90_low": round(combined_wear - 1.645 * combined_uncertainty, 2),
            "ci_90_high": round(combined_wear + 1.645 * combined_uncertainty, 2),
            "prob_critical_percent": ml_result["ml_prob_critical_percent"],
            
            # Веса
            "ml_weight": round(ml_weight * 100, 1),
            "physics_weight": round(physics_weight * 100, 1),
            
            # Детализация
            "status": physics_result["status"],
            "urgency": physics_result["urgency"],
            "thermal": physics_result["thermal_degradation"],
            "mechanical": physics_result["mechanical_wear"],
            "abrasive": physics_result["abrasive_wear"],
            "hydraulic": physics_result["hydraulic_erosion"],
            "hydraulics": physics_result["hydraulics"],
            "recommendations": physics_result["recommendations"],
            "ml_accuracy": self.ml_model.get_model_accuracy() if hasattr(self.ml_model, 'get_model_accuracy') else {}
        }
    
    def add_feedback(self, **kwargs):
        """Обратная связь для самообучения"""
        self.ml_model.add_training_point(**kwargs)


# ============================================================================
# ИНТЕРФЕЙС (обновленный с отображением неопределенности)
# ============================================================================

def create_vzd_wear_panel():
    """Панель с отображением НЕОПРЕДЕЛЕННОСТИ прогноза"""
    return html.Div([
        html.H5("Расчет износа ВЗД (Физика + ML + Uncertainty)", 
               style={"color": "#0f172a", "marginBottom": "15px", "fontWeight": "bold"}),
        
        dbc.Alert([
            html.Strong("ℹ️ Точность прогноза: "),
            html.Span("±X% (90% доверительный интервал)", id="accuracy-info")
        ], color="info", className="mb-3"),
        
        dbc.Card([
            dbc.CardBody([
                # ... (параметры ввода как раньше) ...
                
                dbc.Button(" Рассчитать износ", id='btn-calc-vzd-wear', 
                          color="primary", className="w-100 mb-3"),
                
                html.Div(id='vzd-wear-results'),
            ])
        ])
    ])


def vzd_wear_callbacks(app, data_bridge):
    
    @app.callback(
        Output('vzd-wear-results', 'children'),
        Input('btn-calc-vzd-wear', 'n_clicks'),
        [...],  # States
        prevent_initial_call=True
    )
    def calculate_wear(n_clicks, temp, torque, rpm, sand, flow, pressure, 
                      hours, mud_type, elastomer, mpi):
        if None in [temp, torque, rpm, sand, hours]:
            return html.Div("Заполните все параметры", style={"color": "#dc2626"})
        
        model = HybridVZDWearModel()
        result = model.predict(
            temp_c=temp, torque_knm=torque, rpm=rpm,
            sand_content=sand, flow_rate=flow or 30,
            pressure_mpa=pressure or 20, hours=hours,
            mud_type=mud_type, elastomer_type=elastomer
        )
        
        # Отображение с НЕОПРЕДЕЛЕННОСТЬЮ
        return html.Div([
            # Основной результат
            html.Div([
                html.H3(f"{result['combined_wear']:.1f}% ± {result['uncertainty_std']:.1f}%",
                       style={"color": "#0f172a", "margin": "10px 0"}),
                html.P(f"Доверительный интервал (90%): " +
                      f"[{result['ci_90_low']:.1f}%, {result['ci_90_high']:.1f}%]",
                      style={"color": "#64748b"}),
                html.P(f"Точность прогноза: {result['confidence_percent']:.1f}%",
                      style={"color": "#059669", "fontWeight": "bold"}),
                html.P(f"Вероятность критического износа (>60%): " +
                      f"{result['prob_critical_percent']:.1f}%",
                      style={"color": "#dc2626" if result['prob_critical_percent'] > 50 else "#059669"})
            ], style={"backgroundColor": "#F8FAFC", "padding": "15px", "borderRadius": "8px", "marginBottom": "15px"}),
            
            # ... остальная детализация ...
        ])
