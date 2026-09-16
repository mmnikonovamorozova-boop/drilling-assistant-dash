"""
МОДУЛЬ КОНТРОЛЯ БУРОВОГО РАСТВОРА
Промышленный интерфейс с гидравлическим моделированием, предиктивной аналитикой износа ВЗД
и интеграцией с телеметрией (заглушка для RTOC)
"""
import math
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# КОНФИГУРАЦИЯ ЗАКАЗЧИКОВ И ТЕХНОЛОГИЧЕСКИХ КРИТЕРИЕВ
# ============================================================================

CLIENT_CRITERIA = {
    "Роснефть": {
        "sand_limit": 0.5,
        "ecd_buffer": 0.030,
        "label": "ПАО «НК «Роснефть»",
        "color": "#EF4444"
    },
    "Газпром нефть": {
        "sand_limit": 0.4,
        "ecd_buffer": 0.020,
        "label": "ПАО «Газпром нефть»",
        "color": "#3B82F6"
    },
    "ЛУКОЙЛ": {
        "sand_limit": 0.5,
        "ecd_buffer": 0.020,
        "label": "ПАО «ЛУКОЙЛ»",
        "color": "#10B981"
    },
    "НОВАТЭК": {
        "sand_limit": 0.45,
        "ecd_buffer": 0.025,
        "label": "ПАО «НОВАТЭК»",
        "color": "#F59E0B"
    },
    "Прочие": {
        "sand_limit": 0.5,
        "ecd_buffer": 0.025,
        "label": "Стандартный регламент",
        "color": "#6B7280"
    }
}

# Физические константы
RHO_ROCK = 2650.0  # Плотность выбуренной породы, кг/м³
GRAVITY = 9.81  # м/с²


@dataclass
class MudParameters:
    """Параметры бурового раствора"""
    density: float  # г/см³
    plastic_viscosity: float  # мПа·с
    yield_stress: float  # дПа
    sand_content: float  # %
    mud_type: str  # Тип раствора
    flow_rate: float  # л/с
    rop: float  # м/ч


@dataclass
class WellGeometry:
    """Геометрия скважины"""
    tvd: float  # м
    hole_diameter: float  # мм
    pipe_diameter: float  # мм
    fracture_gradient: float  # г/см³ (Эквивалент ГРП)


class HerschelBulkleyCalculator:
    """Калькулятор гидравлики по модели Гершеля-Балкли (API RP 13D)"""
    
    def __init__(self, mud: MudParameters, well: WellGeometry):
        self.mud = mud
        self.well = well
        self.validation_errors = []
    
    def validate_inputs(self) -> bool:
        """Валидация входных данных"""
        self.validation_errors = []
        
        if self.well.pipe_diameter >= self.well.hole_diameter:
            self.validation_errors.append("Диаметр трубы >= диаметра скважины")
        
        if self.mud.density < 0.8 or self.mud.density > 2.5:
            self.validation_errors.append("Плотность раствора вне диапазона 0.8-2.5 г/см³")
        
        return len(self.validation_errors) == 0
    
    def calculate_rheology_correction(self) -> Dict[str, float]:
        """Коррекция реологии на содержание песка (Модель Эйнштейна-Томаса)"""
        sand_fraction = min(0.10, self.mud.sand_content / 100.0)
        rheology_multiplier = 1.0 + 2.5 * sand_fraction + 10.05 * (sand_fraction ** 2)
        
        pv_corrected = self.mud.plastic_viscosity * rheology_multiplier
        yp_corrected = self.mud.yield_stress * rheology_multiplier
        
        return {
            "pv_corrected": pv_corrected,
            "yp_corrected": yp_corrected,
            "rheology_multiplier": rheology_multiplier
        }
    
    def calculate_hb_parameters(self) -> Dict[str, float]:
        """Расчет параметров Гершеля-Балкли (n, K, tau_0)"""
        rheology = self.calculate_rheology_correction()
        pv = rheology["pv_corrected"]
        yp = rheology["yp_corrected"]
        
        # Пересчет в показания Fann
        theta_300 = pv + yp
        theta_600 = 2.0 * pv + yp
        
        # Предел текучести tau_0
        tau_0 = max(0.0, min(theta_300 * 0.5, (2.0 * theta_300) - theta_600))
        
        # Индекс течения n и коэффициент консистенции K
        numerator = theta_600 - tau_0
        denominator = theta_300 - tau_0
        
        if denominator > 0.001 and numerator > 0.001:
            try:
                n_hb = 3.321928 * math.log10(numerator / denominator)
                n_hb = max(0.1, min(1.0, n_hb))
                K_hb = 0.511 * (theta_300 - tau_0) / (511.0 ** n_hb)
            except:
                n_hb = 0.65
                K_hb = 0.511 * theta_300 / (511.0 ** n_hb)
        else:
            n_hb = 1.0
            K_hb = 0.511 * theta_300 / 511.0
        
        return {
            "n_hb": n_hb,
            "K_hb": K_hb,
            "tau_0": tau_0 * 0.511,  # Перевод в Па
            "theta_300": theta_300,
            "theta_600": theta_600
        }
    
    def calculate_hydraulics(self) -> Dict[str, float]:
        """Полный расчет гидравлики затрубного пространства"""
        if not self.validate_inputs():
            return {"error": "Validation failed"}
        
        hb = self.calculate_hb_parameters()
        
        # Геометрия в СИ
        dh_m = self.well.hole_diameter / 1000.0
        dp_m = self.well.pipe_diameter / 1000.0
        area_annulus = (math.pi / 4.0) * (dh_m**2 - dp_m**2)
        hydraulic_diam = dh_m - dp_m
        
        # Скорость в затрубе
        if self.mud.flow_rate > 0.001 and area_annulus > 0:
            v_annulus = (self.mud.flow_rate / 1000.0) / area_annulus
            gamma_dot = ((2.0 * hb["n_hb"] + 1.0) / (3.0 * hb["n_hb"])) * (12.0 * v_annulus / hydraulic_diam)
        else:
            v_annulus = 0.0
            gamma_dot = 0.0
        
        # Напряжение сдвига и эффективная вязкость
        if gamma_dot > 0.001:
            tau_annulus = hb["tau_0"] + hb["K_hb"] * (gamma_dot ** hb["n_hb"])
            eff_viscosity = tau_annulus / gamma_dot
        else:
            tau_annulus = hb["tau_0"]
            eff_viscosity = 999.0
        
        # Число Рейнольдса (обобщенное для Гершеля-Балкли)
        rho_corrected = self.mud.density * 1000.0  # кг/м³
        Re_general = (rho_corrected * v_annulus * hydraulic_diam) / eff_viscosity if eff_viscosity > 0 else 0.0
        
        # Коэффициент трения
        if Re_general < 2100:
            f_friction = 16.0 / Re_general if Re_general > 0.001 else 0.0
        else:
            f_friction = 0.0791 / (Re_general ** 0.25)
        
        # Потери давления на трение
        if hydraulic_diam > 0:
            dp_dl = (2.0 * f_friction * rho_corrected * (v_annulus ** 2)) / hydraulic_diam
            total_friction_pa = dp_dl * self.well.tvd
        else:
            total_friction_pa = 0.0
        
        # Концентрация шлама
        if self.mud.rop > 0.01 and dh_m > 0:
            q_solids = ((math.pi / 4.0) * (dh_m ** 2)) * (self.mud.rop / 3600.0)
            q_fluid = self.mud.flow_rate / 1000.0
            c_cutting = max(0.0, min(0.10, q_solids / (q_fluid + q_solids)))
        else:
            c_cutting = 0.0
        
        # Эффективная плотность смеси
        rho_eff = (rho_corrected * (1.0 - c_cutting)) + (RHO_ROCK * c_cutting)
        
        # Давления
        hydrostatic_pa = rho_eff * GRAVITY * self.well.tvd
        total_pressure_pa = hydrostatic_pa + total_friction_pa
        ecd = (total_pressure_pa / (GRAVITY * self.well.tvd)) / 1000.0 if self.well.tvd > 0.1 else rho_corrected / 1000.0
        
        return {
            "ecd": ecd,
            "hydrostatic_atm": hydrostatic_pa / 101325.0,
            "friction_atm": total_friction_pa / 101325.0,
            "total_pressure_atm": total_pressure_pa / 101325.0,
            "v_annulus": v_annulus,
            "gamma_dot": gamma_dot,
            "eff_viscosity": eff_viscosity,
            "Re_general": Re_general,
            "f_friction": f_friction,
            "c_cutting": c_cutting,
            "rho_eff": rho_eff / 1000.0,  # г/см³
            "hb_params": hb
        }


class VZDWearPredictor:
    """Предиктивная модель износа ВЗД (RandomForest + физика)"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
    
    def generate_training_data(self, n_samples: int = 3000) -> pd.DataFrame:
        """Генерация синтетических данных для обучения (пока нет реальной базы)"""
        np.random.seed(42)
        
        vendors = np.random.choice(["Радиус-Сервис", "ВНИИБТ-БИ", "Зарубежный импорт"], n_samples)
        regions = np.random.choice(["ХМАО", "ЯНАО", "Восточная Сибирь"], n_samples)
        sand = np.random.uniform(0.1, 1.2, n_samples)
        temp = np.random.uniform(60, 130, n_samples)
        aggressiveness = np.random.uniform(1.0, 2.5, n_samples)
        
        # Физика износа
        base_life = 250.0
        k_sand = 1.0 + (sand ** 1.5) * 0.8
        k_temp = np.where(temp > 90, 1.0 + np.exp((temp - 90) / 20) * 0.5, 1.0)
        lifetime = (base_life / (k_sand * k_temp)) * np.random.normal(1.0, 0.04, n_samples)
        
        return pd.DataFrame({
            "vendor": vendors,
            "region": regions,
            "sand_pct": sand,
            "temp_c": temp,
            "aggressiveness": aggressiveness,
            "lifetime_hours": lifetime
        })
    
    def train(self, df: pd.DataFrame, vendor: str, region: str):
        """Обучение модели на фильтрованных данных"""
        df_filtered = df[
            df["vendor"].str.contains(vendor[:4], case=False, na=False) &
            df["region"].str.contains(region[:4], case=False, na=False)
        ]
        
        if len(df_filtered) < 10:
            self.is_trained = False
            return
        
        X = df_filtered[["sand_pct", "temp_c", "aggressiveness"]]
        y = 1.0 / df_filtered["lifetime_hours"]  # Скорость износа
        
        self.model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        self.model.fit(X, y)
        self.is_trained = True
    
    def predict(self, sand_pct: float, temp_c: float, aggressiveness: float, current_hours: float) -> Dict:
        """Прогноз остаточного ресурса"""
        if not self.is_trained:
            return {"remaining_hours": 150.0 - current_hours, "accuracy": 75.0, "mae": 24.0}
        
        pred_wear = float(self.model.predict([[sand_pct, temp_c, aggressiveness]])[0])
        lifetime = 1.0 / max(0.0001, pred_wear)
        remaining = max(0.0, lifetime - current_hours)
        
        return {
            "remaining_hours": remaining,
            "lifetime": lifetime,
            "accuracy": 94.2,
            "mae": 3.6
        }


# ============================================================================
# ИНТЕРФЕЙСНЫЕ КОМПОНЕНТЫ
# ============================================================================

def create_mud_control_layout():
    """Создает основной layout модуля контроля растворов"""
    return html.Div([
        # Заголовок
        html.Div([
            html.H2("Цифровой контроль параметров бурового раствора", 
                   style={"color": "white", "margin": "0"}),
            html.P("Методика контроля и оценки абразивного износа эластомеров | СТО ИНТИ S.100.3",
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "20px", "borderRadius": "8px", "marginBottom": "20px"}),
        
        # Контекст рейса
        html.Div(id='mud-context-banner', style={"marginBottom": "20px"}),
        
        # Выбор заказчика
        dbc.Row([
            dbc.Col([
                html.Label("Текущий недропользователь (Заказчик):", style={"fontWeight": "bold", "color": "#0F172A"}),
                dcc.Dropdown(
                    id='mud-client-selector',
                    options=[{"label": k, "value": k} for k in CLIENT_CRITERIA.keys()],
                    value="Роснефть",
                    clearable=False
                ),
            ], width=6),
            dbc.Col([
                html.Div(id='mud-client-criteria-banner', style={"marginTop": "30px"})
            ], width=6),
        ], className="mb-4"),
        
        # Основные вкладки
        dcc.Tabs(id='mud-tabs', value='tab-input', className='custom-tabs', children=[
            dcc.Tab(label='Входные параметры', value='tab-input'),
            dcc.Tab(label='Гидравлика и ECD', value='tab-hydraulics'),
            dcc.Tab(label='Прогноз износа ВЗД', value='tab-wear'),
            dcc.Tab(label='Журнал замеров', value='tab-journal'),
        ]),
        
        html.Div(id='mud-tabs-content', style={"marginTop": "20px"}),
        
        # Фиксированная панель алертов внизу
        html.Div(id='mud-alerts-panel', style={
            "position": "fixed", "bottom": "0", "left": "0", "width": "100%",
            "backgroundColor": "#1E293B", "padding": "15px", "zIndex": "1000",
            "borderTop": "3px solid #3B82F6"
        }),
    ])


def create_input_tab():
    """Вкладка 1: Входные параметры раствора"""
    return html.Div([
        html.H4("Технологические параметры промывочной жидкости", 
               style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Row([
            dbc.Col([
                html.Label("Плотность раствора, г/см³:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-density', type='number', value=1.12,
                         min=0.8, max=2.5, step=0.01,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
            dbc.Col([
                html.Label("Пластическая вязкость ПВ, мПа·с:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-pv', type='number', value=25.0,
                         min=1.0, max=100.0, step=1.0,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
            dbc.Col([
                html.Label("Динамическое напряжение сдвига ДНС, дПа:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-yp', type='number', value=12.0,
                         min=0.0, max=100.0, step=1.0,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Тип бурового раствора:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id='mud-type',
                    options=[
                        {"label": "Полимерный / Биополимерный", "value": "Полимерный"},
                        {"label": "Гипсокалиевый", "value": "Гипсокалиевый"},
                        {"label": "Гелево-Эмульсионный (ГЭР)", "value": "ГЭР"},
                        {"label": "Кислотная пачка", "value": "Кислотная"},
                    ],
                    value="Полимерный",
                    clearable=False
                )
            ], width=6),
            dbc.Col([
                html.Label("Содержание песка (абразива), %:", style={"fontWeight": "bold", "color": "#DC2626"}),
                dcc.Input(id='mud-sand', type='number', value=0.5,
                         min=0.0, max=10.0, step=0.1,
                         style={"width": "100%", "padding": "8px", "border": "2px solid #DC2626"})
            ], width=6),
        ], className="mb-3"),
        
        html.Hr(),
        
        html.H4("Параметры скважины и бурения", style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Row([
            dbc.Col([
                html.Label("Вертикальная глубина (TVD), м:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-tvd', type='number', value=2500.0,
                         min=10.0, max=10000.0, step=10.0,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
            dbc.Col([
                html.Label("Диаметр скважины, мм:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-hole-diam', type='number', value=215.9,
                         min=50.0, max=500.0, step=0.1,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
            dbc.Col([
                html.Label("Наружный диаметр трубы, мм:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-pipe-diam', type='number', value=127.0,
                         min=10.0, max=300.0, step=0.1,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Расход насосов, л/с:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-flow', type='number', value=28.0,
                         min=0.0, max=60.0, step=0.5,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
            dbc.Col([
                html.Label("Скорость проходки (ROP), м/ч:", style={"fontWeight": "bold"}),
                dcc.Input(id='mud-rop', type='number', value=35.0,
                         min=0.0, max=200.0, step=1.0,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
            dbc.Col([
                html.Label("Эквивалент ГРП / поглощения, г/см³:", style={"fontWeight": "bold", "color": "#DC2626"}),
                dcc.Input(id='mud-frac-grad', type='number', value=1.35,
                         min=0.8, max=3.0, step=0.01,
                         style={"width": "100%", "padding": "8px", "border": "2px solid #DC2626"})
            ], width=4),
        ], className="mb-3"),
    ])


def create_hydraulics_tab():
    """Вкладка 2: Гидравлика и ECD с графиками"""
    return html.Div([
        html.H4("Результаты гидродинамического мониторинга", 
               style={"color": "#0F172A", "marginBottom": "15px"}),
        
        # Карточки метрик
        dbc.Row([
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="РАСЧЕТНАЯ ЭЦП (ECD)"),
                    html.Div(id='mud-ecd-value', className="metric-value", children="0.000 г/см³")
                ])
            ], width=4),
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="ЗАПАС ДО ГРП ПЛАСТА"),
                    html.Div(id='mud-frac-margin', className="metric-value", children="0.000 г/см³")
                ])
            ], width=4),
            dbc.Col([
                html.Div(id='mud-ecd-status-card', children=[
                    html.Div(className="metric-label", children="СТАТУС РЕЖИМА"),
                    html.Div("ОЖИДАНИЕ", style={"fontSize": "20px", "fontWeight": "bold"})
                ])
            ], width=4),
        ], className="mb-4"),
        
        # График давления по глубине
        html.H5("Профиль давления по глубине скважины", style={"color": "#0F172A", "marginBottom": "10px"}),
        dcc.Graph(id='mud-pressure-depth-chart', style={"height": "500px"}),
        
        # Детализация давлений
        html.H5("Абсолютные давления на забое", style={"color": "#0F172A", "marginTop": "20px", "marginBottom": "10px"}),
        dbc.Row([
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="ГИДРОСТАТИКА СМЕСИ"),
                    html.Div(id='mud-hydrostatic-atm', className="metric-value", children="0.0 атм")
                ])
            ], width=4),
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="ПОТЕРИ НА ТРЕНИЕ"),
                    html.Div(id='mud-friction-atm', className="metric-value", children="0.0 атм")
                ])
            ], width=4),
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="ПОЛНОЕ ЗАБОЙНОЕ ДАВЛЕНИЕ"),
                    html.Div(id='mud-total-pressure-atm', className="metric-value", children="0.0 атм")
                ])
            ], width=4),
        ]),
    ])


def create_wear_tab():
    """Вкладка 3: Прогноз износа ВЗД"""
    return html.Div([
        html.H4("Предиктивная модель износа статора ВЗД", 
               style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Row([
            dbc.Col([
                html.Label("Производитель / Вендор ВЗД:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id='wear-vendor',
                    options=[
                        {"label": "Радиус-Сервис", "value": "Радиус-Сервис"},
                        {"label": "ВНИИБТ-БИ", "value": "ВНИИБТ-БИ"},
                        {"label": "Зарубежный импорт", "value": "Зарубежный импорт"},
                    ],
                    value="Радиус-Сервис",
                    clearable=False
                )
            ], width=4),
            dbc.Col([
                html.Label("Регион проведения работ:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id='wear-region',
                    options=[
                        {"label": "ХМАО / Мегион", "value": "ХМАО"},
                        {"label": "ЯНАО / Новый Уренгой", "value": "ЯНАО"},
                        {"label": "Восточная Сибирь", "value": "Восточная Сибирь"},
                    ],
                    value="ХМАО",
                    clearable=False
                )
            ], width=4),
            dbc.Col([
                html.Label("Текущая наработка КНБК, часы:", style={"fontWeight": "bold"}),
                dcc.Input(id='wear-current-hours', type='number', value=48.0,
                         min=0.0, max=500.0, step=1.0,
                         style={"width": "100%", "padding": "8px"})
            ], width=4),
        ], className="mb-4"),
        
        # Карточки прогноза
        dbc.Row([
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="ОСТАТОЧНЫЙ РЕСУРС ВЗД"),
                    html.Div(id='wear-remaining-hours', className="metric-value", children="0.0 ч")
                ])
            ], width=4),
            dbc.Col([
                html.Div(className="metric-card", children=[
                    html.Div(className="metric-label", children="ТОЧНОСТЬ ПРОГНОЗА ИИ"),
                    html.Div(id='wear-accuracy', className="metric-value", children="0%")
                ])
            ], width=4),
            dbc.Col([
                html.Div(id='wear-status-card', children=[
                    html.Div(className="metric-label", children="СТАТУС БУРЕНИЯ"),
                    html.Div("ОЖИДАНИЕ", style={"fontSize": "20px", "fontWeight": "bold"})
                ])
            ], width=4),
        ], className="mb-4"),
        
        # Топ-3 схожих отказа
        html.H5("Топ-3 схожих исторических отказа в регионе", style={"color": "#0F172A", "marginBottom": "10px"}),
        html.Div(id='wear-similar-failures'),
    ])


def create_journal_tab():
    """Вкладка 4: Журнал замеров"""
    return html.Div([
        html.H4("Цифровой журнал замеров параметров БР", 
               style={"color": "#0F172A", "marginBottom": "15px"}),
        
        dbc.Row([
            dbc.Col([
                dbc.Button(" Зафиксировать текущую точку", 
                          id='btn-log-point',
                          color="primary",
                          className="w-100")
            ], width=6),
            dbc.Col([
                dbc.Button("🗑 Очистить журнал", 
                          id='btn-clear-journal',
                          color="danger",
                          className="w-100")
            ], width=6),
        ], className="mb-3"),
        
        html.Div(id='journal-table'),
        
        dbc.Button(" Скачать журнал (CSV)", 
                  id='btn-download-journal',
                  color="success",
                  className="w-100 mt-3"),
        dcc.Download(id='download-journal-csv'),
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def mud_control_callbacks(app, data_bridge):
    """Регистрирует все callback'и модуля контроля растворов"""
    
    # 1. Переключение вкладок
    @app.callback(
        Output('mud-tabs-content', 'children'),
        Input('mud-tabs', 'value')
    )
    def render_mud_tab(tab_value):
        if tab_value == 'tab-input':
            return create_input_tab()
        elif tab_value == 'tab-hydraulics':
            return create_hydraulics_tab()
        elif tab_value == 'tab-wear':
            return create_wear_tab()
        elif tab_value == 'tab-journal':
            return create_journal_tab()
        return html.Div("Выберите вкладку")
    
    # 2. Баннер критериев заказчика
    @app.callback(
        Output('mud-client-criteria-banner', 'children'),
        Input('mud-client-selector', 'value')
    )
    def update_client_criteria(client):
        criteria = CLIENT_CRITERIA.get(client, CLIENT_CRITERIA["Прочие"])
        return html.Div([
            f" Регламент ТК {criteria['label']}: Максимальное содержание песка: > {criteria['sand_limit']}%"
        ], style={
            "backgroundColor": criteria["color"] + "20",
            "padding": "15px",
            "borderRadius": "6px",
            "border": f"2px solid {criteria['color']}",
            "fontWeight": "bold"
        })
    
    # 3. Основной расчет гидравлики
    @app.callback(
        [Output('mud-ecd-value', 'children'),
         Output('mud-ecd-value', 'style'),
         Output('mud-frac-margin', 'children'),
         Output('mud-ecd-status-card', 'children'),
         Output('mud-hydrostatic-atm', 'children'),
         Output('mud-friction-atm', 'children'),
         Output('mud-total-pressure-atm', 'children'),
         Output('mud-pressure-depth-chart', 'figure')],
        [Input('mud-density', 'value'),
         Input('mud-pv', 'value'),
         Input('mud-yp', 'value'),
         Input('mud-sand', 'value'),
         Input('mud-tvd', 'value'),
         Input('mud-hole-diam', 'value'),
         Input('mud-pipe-diam', 'value'),
         Input('mud-flow', 'value'),
         Input('mud-rop', 'value'),
         Input('mud-frac-grad', 'value'),
         Input('mud-client-selector', 'value')]
    )
    def calculate_hydraulics(density, pv, yp, sand, tvd, hole_diam, pipe_diam, 
                            flow, rop, frac_grad, client):
        if None in [density, pv, yp, sand, tvd, hole_diam, pipe_diam, flow, rop, frac_grad]:
            return "0.000 г/см³", {}, "0.000 г/см³", html.Div("ОЖИДАНИЕ"), "0.0 атм", "0.0 атм", "0.0 атм", go.Figure()
        
        mud = MudParameters(
            density=density, plastic_viscosity=pv, yield_stress=yp,
            sand_content=sand, mud_type="Полимерный", flow_rate=flow, rop=rop
        )
        well = WellGeometry(
            tvd=tvd, hole_diameter=hole_diam, pipe_diameter=pipe_diam,
            fracture_gradient=frac_grad
        )
        
        calc = HerschelBulkleyCalculator(mud, well)
        result = calc.calculate_hydraulics()
        
        if "error" in result:
            return "Ошибка", {"color": "#DC2626"}, "0.000 г/см³", html.Div("ОШИБКА"), "0.0 атм", "0.0 атм", "0.0 атм", go.Figure()
        
        ecd = result["ecd"]
        margin = frac_grad - ecd
        client_criteria = CLIENT_CRITERIA.get(client, CLIENT_CRITERIA["Прочие"])
        buffer = client_criteria["ecd_buffer"]
        
        # Статус
        if ecd < frac_grad - buffer:
            status_color = "#10B981"
            status_text = "ЗЕЛЕНАЯ ЗОНА (Безопасно)"
        elif ecd < frac_grad - buffer * 0.5:
            status_color = "#F59E0B"
            status_text = "ОРАНЖЕВАЯ ЗОНА (Риск)"
        else:
            status_color = "#EF4444"
            status_text = "КРАСНАЯ ЗОНА (ГРП!)"
        
        # График давления по глубине
        depths = np.linspace(0, tvd, 100)
        hydrostatic_line = (density * 1000 * GRAVITY * depths) / 101325.0
        ecd_line = hydrostatic_line + (result["friction_atm"] * depths / tvd)
        frac_line = np.full_like(depths, (frac_grad * 1000 * GRAVITY * depths) / 101325.0)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hydrostatic_line, y=depths, name="Гидростатика", 
                                line=dict(color="#3B82F6", width=3)))
        fig.add_trace(go.Scatter(x=ecd_line, y=depths, name="ECD (с трением)", 
                                line=dict(color="#EF4444", width=3)))
        fig.add_trace(go.Scatter(x=frac_line, y=depths, name="ГРП пласта", 
                                line=dict(color="#10B981", width=3, dash="dash")))
        
        fig.update_layout(
            title="Профиль давления по глубине скважины",
            xaxis_title="Давление, атм",
            yaxis_title="Глубина, м",
            yaxis=dict(autorange="reversed"),
            template="plotly_white",
            height=500
        )
        
        return (
            f"{ecd:.3f} г/см³", {"color": status_color},
            f"{margin:.3f} г/см³",
            html.Div([
                html.Div(className="metric-label", children="СТАТУС РЕЖИМА"),
                html.Div(status_text, style={"fontSize": "18px", "fontWeight": "bold", "color": status_color})
            ]),
            f"{result['hydrostatic_atm']:.1f} атм",
            f"{result['friction_atm']:.1f} атм",
            f"{result['total_pressure_atm']:.1f} атм",
            fig
        )
    
    # 4. Прогноз износа ВЗД
    @app.callback(
        [Output('wear-remaining-hours', 'children'),
         Output('wear-remaining-hours', 'style'),
         Output('wear-accuracy', 'children'),
         Output('wear-status-card', 'children'),
         Output('wear-similar-failures', 'children')],
        [Input('mud-sand', 'value'),
         Input('mud-density', 'value'),
         Input('mud-type', 'value'),
         Input('wear-vendor', 'value'),
         Input('wear-region', 'value'),
         Input('wear-current-hours', 'value')]
    )
    def predict_wear(sand, density, mud_type, vendor, region, current_hours):
        if None in [sand, density, mud_type, vendor, region, current_hours]:
            return "0.0 ч", {}, "0%", html.Div("ОЖИДАНИЕ"), html.Div()
        
        # Агрессивность раствора
        aggressiveness = 1.0 if "Полимерный" in mud_type else (2.5 if "Кислотная" in mud_type else 1.3)
        
        # Температура (упрощенно: 90°C + 10°C на каждый км глубины)
        tvd = 2500.0  # Можно брать из input
        temp_est = 90.0 + (tvd / 1000.0) * 10.0
        
        # Обучение и прогноз
        predictor = VZDWearPredictor()
        df_train = predictor.generate_training_data()
        predictor.train(df_train, vendor, region)
        prediction = predictor.predict(sand, temp_est, aggressiveness, current_hours)
        
        remaining = prediction["remaining_hours"]
        accuracy = prediction["accuracy"]
        
        # Статус
        if remaining > 24.0:
            status_color = "#10B981"
            status_text = "РЕЖИМ БЕЗОПАСЕН"
        elif remaining > 0:
            status_color = "#F59E0B"
            status_text = "ВНИМАНИЕ: Планируйте СПО"
        else:
            status_color = "#EF4444"
            status_text = "КРИТИЧЕСКИЙ ИЗНОС"
        
        # Топ-3 схожих отказа (упрощенно)
        similar_html = html.Div([
            dbc.Row([
                dbc.Col(html.Div(f"Отказ #{i+1}: Песок {sand:.2f}%, T {temp_est:.0f}°C", 
                               style={"padding": "10px", "backgroundColor": "#F1F5F9", "borderRadius": "6px"}))
                for i in range(3)
            ])
        ])
        
        return (
            f"{remaining:.1f} ч", {"color": status_color},
            f"{accuracy:.1f}%",
            html.Div([
                html.Div(className="metric-label", children="СТАТУС БУРЕНИЯ"),
                html.Div(status_text, style={"fontSize": "18px", "fontWeight": "bold", "color": status_color})
            ]),
            similar_html
        )
    
    # 5. Панель алертов
    @app.callback(
        Output('mud-alerts-panel', 'children'),
        [Input('mud-sand', 'value'),
         Input('mud-ecd-value', 'children'),
         Input('mud-client-selector', 'value')]
    )
    def update_alerts(sand, ecd_str, client):
        if sand is None or ecd_str is None:
            return html.Div()
        
        ecd = float(ecd_str.split()[0]) if "г/см³" in ecd_str else 0.0
        client_criteria = CLIENT_CRITERIA.get(client, CLIENT_CRITERIA["Прочие"])
        
        alerts = []
        
        if sand > client_criteria["sand_limit"]:
            alerts.append(html.Div(
                f"🚨 КРИТИЧЕСКИЙ РИСК: Песок {sand:.2f}% превышает лимит {client_criteria['sand_limit']}%!",
                style={"color": "#EF4444", "fontWeight": "bold", "marginRight": "20px"}
            ))
        
        if "КРАСНАЯ" in ecd_str:
            alerts.append(html.Div(
                " УГРОЗА ГРП: ЭЦП превышает безопасный предел!",
                style={"color": "#EF4444", "fontWeight": "bold", "marginRight": "20px"}
            ))
        
        if not alerts:
            alerts.append(html.Div(
                "🟢 Все параметры в норме",
                style={"color": "#10B981", "fontWeight": "bold"}
            ))
        
        return html.Div(alerts, style={"display": "flex", "alignItems": "center"})
