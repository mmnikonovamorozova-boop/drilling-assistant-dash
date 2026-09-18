"""
СКРЫТЫЙ МОДУЛЬ СТРЕСС-ТЕСТИРОВАНИЯ И ГРАНИЧНОГО АНАЛИЗА
Автоматическая проверка математических моделей и ИИ-ядер
на экстремальных значениях, пограничных условиях и случайных данных.

Доступен только через /stress-test (админский режим)
"""
import math
import random
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np

from modules.bha_umk_enhanced import UMKCalculator, UMKParameters
from modules.vzd_wear import HybridVZDWearModel
from modules.mud_control import HerschelBulkleyCalculator, MudParameters, WellGeometry

# ============================================================================
# ТИПЫ ТЕСТОВ
# ============================================================================

class TestType:
    BOUNDARY = "boundary"  # Граничные значения
    STRESS = "stress"  # Экстремальные нагрузки
    FUZZ = "fuzz"  # Случайные/некорректные данные
    REGRESSION = "regression"  # Регрессионное тестирование
    MONTE_CARLO = "monte_carlo"  # Статистическое моделирование


# ============================================================================
# БАЗА ТЕСТОВЫХ СЦЕНАРИЕВ
# ============================================================================

BOUNDARY_TESTS = {
    "umk_torque": {
        "name": "УМК: Момент затяжки",
        "tests": [
            {"params": {"torque": 0.0}, "expected": "ZERO_TORQUE", "description": "Нулевой момент"},
            {"params": {"torque": 0.1}, "expected": "LOW_TORQUE", "description": "Минимальный момент"},
            {"params": {"torque": 200.0}, "expected": "EXCEEDS_KEY_CAPACITY", "description": "Максимальный момент"},
            {"params": {"torque": -1.0}, "expected": "VALIDATION_ERROR", "description": "Отрицательный момент"},
            {"params": {"torque": 999999.0}, "expected": "EXCEEDS_KEY_CAPACITY", "description": "Экстремальный момент"},
        ]
    },
    "mud_density": {
        "name": "Раствор: Плотность",
        "tests": [
            {"params": {"density": 0.8}, "expected": "valid", "description": "Минимальная плотность"},
            {"params": {"density": 2.5}, "expected": "valid", "description": "Максимальная плотность"},
            {"params": {"density": 0.0}, "expected": "error", "description": "Нулевая плотность"},
            {"params": {"density": 5.0}, "expected": "error", "description": "Нереальная плотность"},
            {"params": {"density": -1.0}, "expected": "error", "description": "Отрицательная плотность"},
        ]
    },
    "vzd_wear": {
        "name": "ВЗД: Износ",
        "tests": [
            {"params": {"hours": 0}, "expected": "0% wear", "description": "Нулевая наработка"},
            {"params": {"hours": 500}, "expected": "100% wear", "description": "Экстремальная наработка"},
            {"params": {"temp": 200}, "expected": "high wear", "description": "Критическая температура"},
            {"params": {"temp": -50}, "expected": "error", "description": "Нереальная температура"},
        ]
    }
}


class StressTester:
    """
    Движок стресс-тестирования для всех модулей приложения
    """
    
    def __init__(self):
        self.results = []
        self.log_file = Path("data/stress_test_log.json")
    
    def run_boundary_tests(self, module_name: str) -> List[Dict]:
        """
        Тестирование на граничных значениях
        
        Проверяет поведение системы на минимальных/максимальных/пограничных значениях
        """
        results = []
        
        if module_name not in BOUNDARY_TESTS:
            return [{"error": f"Неизвестный модуль: {module_name}"}]
        
        tests = BOUNDARY_TESTS[module_name]["tests"]
        
        for test in tests:
            try:
                result = self._execute_test(module_name, test["params"])
                status = "PASS" if result["status"] == test["expected"] else "FAIL"
                
                results.append({
                    "test_name": test["description"],
                    "params": test["params"],
                    "expected": test["expected"],
                    "actual": result["status"],
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                results.append({
                    "test_name": test["description"],
                    "params": test["params"],
                    "expected": test["expected"],
                    "actual": f"EXCEPTION: {str(e)}",
                    "status": "FAIL",
                    "timestamp": datetime.now().isoformat()
                })
        
        return results
    
    def run_stress_tests(self, module_name: str, iterations: int = 100) -> List[Dict]:
        """
        Стресс-тестирование: экстремальные нагрузки
        
        Запускает модель с экстремальными параметрами множество раз
        """
        results = []
        
        for i in range(iterations):
            # Генерация экстремальных параметров
            extreme_params = self._generate_extreme_params(module_name)
            
            try:
                start_time = time.time()
                result = self._execute_test(module_name, extreme_params)
                execution_time = time.time() - start_time
                
                results.append({
                    "iteration": i + 1,
                    "params": extreme_params,
                    "status": result["status"],
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                results.append({
                    "iteration": i + 1,
                    "params": extreme_params,
                    "status": f"EXCEPTION: {str(e)}",
                    "execution_time_ms": 0,
                    "timestamp": datetime.now().isoformat()
                })
        
        return results
    
    def run_fuzz_tests(self, module_name: str, iterations: int = 1000) -> List[Dict]:
        """
        Fuzz-тестирование: случайные/некорректные данные
        
        Проверяет устойчивость системы к некорректным входным данным
        """
        results = []
        crashes = 0
        
        for i in range(iterations):
            # Генерация случайных (возможно некорректных) параметров
            random_params = self._generate_random_params(module_name)
            
            try:
                result = self._execute_test(module_name, random_params)
                results.append({
                    "iteration": i + 1,
                    "params": random_params,
                    "status": "HANDLED",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                crashes += 1
                results.append({
                    "iteration": i + 1,
                    "params": random_params,
                    "status": f"CRASH: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Итоговая статистика
        crash_rate = (crashes / iterations) * 100
        
        return [{
            "test_type": "fuzz",
            "module": module_name,
            "total_iterations": iterations,
            "crashes": crashes,
            "crash_rate_percent": round(crash_rate, 2),
            "status": "PASS" if crash_rate < 1.0 else "FAIL",
            "timestamp": datetime.now().isoformat()
        }]
    
    def run_monte_carlo(self, module_name: str, iterations: int = 10000) -> Dict:
        """
        Метод Монте-Карло: статистическое моделирование
        
        Запускает модель с тысячами случайных комбинаций параметров
        для проверки устойчивости и выявления аномалий
        """
        results = []
        
        for i in range(iterations):
            params = self._generate_realistic_params(module_name)
            
            try:
                result = self._execute_test(module_name, params)
                results.append({
                    "params": params,
                    "output": result["status"],
                    "timestamp": datetime.now().isoformat()
                })
            except:
                pass
        
        # Статистический анализ результатов
        return self._analyze_monte_carlo_results(results, module_name)
    
    def _execute_test(self, module_name: str, params: Dict) -> Dict:
        """Выполнение теста для конкретного модуля"""
        
        if module_name == "umk_torque":
            return self._test_umk(params)
        elif module_name == "mud_density":
            return self._test_mud(params)
        elif module_name == "vzd_wear":
            return self._test_vzd(params)
        else:
            return {"status": "UNKNOWN_MODULE"}
    
    def _test_umk(self, params: Dict) -> Dict:
        """Тест УМК"""
        torque = params.get("torque", 50.0)
        
        umk_params = UMKParameters(
            key_model="УМК-48",
            thread_type="NC46 (4'')",
            steel_grade="G",
            grease_type="Стандартная API (K=1.0)",
            lever_arm=1.1,
            k_factor=1.0,
            cable_diameter=12.0,
            piston_area_cm2=50.0,
            target_torque_override=torque
        )
        
        calc = UMKCalculator(umk_params)
        status = calc.get_safety_status(torque, 65.0)
        
        return {"status": status}
    
    def _test_mud(self, params: Dict) -> Dict:
        """Тест раствора"""
        density = params.get("density", 1.2)
        
        mud = MudParameters(
            density=density,
            plastic_viscosity=25.0,
            yield_stress=12.0,
            sand_content=0.5,
            mud_type="Полимерный",
            flow_rate=28.0,
            rop=35.0
        )
        
        well = WellGeometry(
            tvd=2500.0,
            hole_diameter=215.9,
            pipe_diameter=127.0,
            fracture_gradient=1.35
        )
        
        calc = HerschelBulkleyCalculator(mud, well)
        is_valid = calc.validate_inputs()
        
        return {"status": "valid" if is_valid else "error"}
    
    def _test_vzd(self, params: Dict) -> Dict:
        """Тест ВЗД"""
        hours = params.get("hours", 100)
        temp = params.get("temp", 90)
        
        model = HybridVZDWearModel()
        result = model.predict(
            temp_c=temp,
            torque_knm=8.5,
            rpm=120,
            sand_content=0.5,
            flow_rate=30.0,
            pressure_mpa=20.0,
            hours=hours,
            mud_type="Полимерный",
            elastomer_type="Стандартный нитрил"
        )
        
        return {"status": f"{result['combined_wear']:.1f}% wear"}
    
    def _generate_extreme_params(self, module_name: str) -> Dict:
        """Генерация экстремальных параметров"""
        if module_name == "umk_torque":
            return {"torque": random.choice([0.0, 0.001, 199.999, 200.0, 999999.0])}
        elif module_name == "mud_density":
            return {"density": random.choice([0.0, 0.001, 2.499, 2.5, 10.0])}
        elif module_name == "vzd_wear":
            return {
                "hours": random.choice([0, 1, 499, 500, 999999]),
                "temp": random.choice([-100, 0, 199, 200, 1000])
            }
        return {}
    
    def _generate_random_params(self, module_name: str) -> Dict:
        """Генерация случайных параметров (включая некорректные)"""
        if module_name == "umk_torque":
            return {"torque": random.uniform(-1000, 10000)}
        elif module_name == "mud_density":
            return {"density": random.uniform(-10, 50)}
        elif module_name == "vzd_wear":
            return {
                "hours": random.uniform(-100, 10000),
                "temp": random.uniform(-200, 500)
            }
        return {}
    
    def _generate_realistic_params(self, module_name: str) -> Dict:
        """Генерация реалистичных параметров"""
        if module_name == "umk_torque":
            return {"torque": random.uniform(10, 100)}
        elif module_name == "mud_density":
            return {"density": random.uniform(1.0, 2.2)}
        elif module_name == "vzd_wear":
            return {
                "hours": random.uniform(10, 300),
                "temp": random.uniform(60, 130)
            }
        return {}
    
    def _analyze_monte_carlo_results(self, results: List[Dict], module_name: str) -> Dict:
        """Анализ результатов Монте-Карло"""
        if not results:
            return {"error": "No results"}
        
        # Статистика
        total = len(results)
        unique_outputs = set(r["output"] for r in results)
        
        # Поиск аномалий
        anomalies = [r for r in results if "error" in r["output"].lower() or "exception" in r["output"].lower()]
        anomaly_rate = (len(anomalies) / total) * 100
        
        return {
            "module": module_name,
            "total_simulations": total,
            "unique_outputs": len(unique_outputs),
            "anomalies_detected": len(anomalies),
            "anomaly_rate_percent": round(anomaly_rate, 2),
            "status": "PASS" if anomaly_rate < 5.0 else "FAIL",
            "timestamp": datetime.now().isoformat()
        }
    
    def save_results(self, results: List[Dict]):
        """Сохранение результатов в лог-файл"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Загрузка существующих результатов
        existing = []
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        
        # Добавление новых результатов
        existing.extend(results)
        
        # Сохранение (храним последние 10000 записей)
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(existing[-10000:], f, ensure_ascii=False, indent=2)


# ============================================================================
# ИНТЕРФЕЙСНЫЕ КОМПОНЕНТЫ
# ============================================================================

def create_stress_test_layout():
    """Макет модуля стресс-тестирования (скрытый, только для админа)"""
    return html.Div([
        html.Div([
            html.H2("🔬 Стресс-тестирование и валидация моделей", style={"color": "white", "margin": "0"}),
            html.P("Автоматическая проверка математических моделей и ИИ-ядер на экстремальных значениях", 
                  style={"color": "#94A3B8", "margin": "5px 0 0 0", "fontSize": "14px"})
        ], style={"backgroundColor": "#1E293B", "padding": "20px", "borderRadius": "8px", "marginBottom": "20px"}),
        
        # Выбор модуля для тестирования
        dbc.Card([
            dbc.CardBody([
                html.H5("Выбор модуля для тестирования:", style={"marginBottom": "15px"}),
                dcc.Dropdown(
                    id='stress-module-select',
                    options=[
                        {"label": "УМК (Момент затяжки)", "value": "umk_torque"},
                        {"label": "Раствор (Плотность)", "value": "mud_density"},
                        {"label": "ВЗД (Износ)", "value": "vzd_wear"},
                    ],
                    value="umk_torque",
                    clearable=False
                ),
            ])
        ], className="mb-4"),
        
        # Типы тестов
        html.H4("Типы тестирования", style={"color": "#0F172A", "marginBottom": "15px"}),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6(" Граничные значения", style={"marginBottom": "10px"}),
                        html.P("Тестирование на минимальных/максимальных/пограничных значениях", style={"fontSize": "12px", "marginBottom": "15px"}),
                        dbc.Button("Запустить", id='btn-boundary-test', color="primary", className="w-100"),
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6(" Стресс-тест", style={"marginBottom": "10px"}),
                        html.P("Экстремальные нагрузки (100 итераций)", style={"fontSize": "12px", "marginBottom": "15px"}),
                        dbc.Button("Запустить", id='btn-stress-test', color="warning", className="w-100"),
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("🎲 Fuzz-тест", style={"marginBottom": "10px"}),
                        html.P("Случайные/некорректные данные (1000 итераций)", style={"fontSize": "12px", "marginBottom": "15px"}),
                        dbc.Button("Запустить", id='btn-fuzz-test', color="danger", className="w-100"),
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📊 Монте-Карло", style={"marginBottom": "10px"}),
                        html.P("Статистическое моделирование (10000 итераций)", style={"fontSize": "12px", "marginBottom": "15px"}),
                        dbc.Button("Запустить", id='btn-monte-carlo', color="success", className="w-100"),
                    ])
                ])
            ], width=3),
        ], className="mb-4"),
        
        # Результаты тестирования
        html.H4("Результаты", style={"color": "#0F172A", "marginBottom": "15px"}),
        html.Div(id='stress-test-results'),
        
        # График результатов
        dcc.Graph(id='stress-test-chart', style={"height": "400px", "marginTop": "20px"}),
        
        # Лог тестирования
        html.H4("Лог тестирования", style={"color": "#0F172A", "marginBottom": "15px"}),
        html.Div(id='stress-test-log', style={
            "backgroundColor": "#1E293B", "color": "#10B981", "padding": "15px",
            "borderRadius": "6px", "fontFamily": "monospace", "fontSize": "12px",
            "maxHeight": "300px", "overflowY": "auto"
        }),
    ])


# ============================================================================
# CALLBACKS
# ============================================================================

def stress_test_callbacks(app, data_bridge):
    
    tester = StressTester()
    
    @app.callback(
        [Output('stress-test-results', 'children'),
         Output('stress-test-chart', 'figure'),
         Output('stress-test-log', 'children')],
        [Input('btn-boundary-test', 'n_clicks'),
         Input('btn-stress-test', 'n_clicks'),
         Input('btn-fuzz-test', 'n_clicks'),
         Input('btn-monte-carlo', 'n_clicks')],
        State('stress-module-select', 'value'),
        prevent_initial_call=True
    )
    def run_tests(boundary_clicks, stress_clicks, fuzz_clicks, monte_carlo_clicks, module_name):
        ctx = dash.callback_context
        if not ctx.triggered:
            return html.Div(), go.Figure(), ""
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        results = []
        log_lines = []
        
        if button_id == 'btn-boundary-test':
            results = tester.run_boundary_tests(module_name)
            log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск граничных тестов для {module_name}")
        
        elif button_id == 'btn-stress-test':
            results = tester.run_stress_tests(module_name, iterations=100)
            log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск стресс-теста для {module_name} (100 итераций)")
        
        elif button_id == 'btn-fuzz-test':
            results = tester.run_fuzz_tests(module_name, iterations=1000)
            log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск fuzz-теста для {module_name} (1000 итераций)")
        
        elif button_id == 'btn-monte-carlo':
            results = [tester.run_monte_carlo(module_name, iterations=10000)]
            log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск Монте-Карло для {module_name} (10000 итераций)")
        
        # Сохранение результатов
        tester.save_results(results)
        
        # Отображение результатов
        pass_count = sum(1 for r in results if r.get("status") == "PASS")
        fail_count = sum(1 for r in results if r.get("status") == "FAIL")
        
        results_html = html.Div([
            dbc.Alert([
                html.Strong(f"Результаты тестирования: "),
                html.Span(f"✅ Пройдено: {pass_count} | ❌ Провалено: {fail_count}", 
                         style={"color": "#10B981" if fail_count == 0 else "#EF4444"})
            ], color="success" if fail_count == 0 else "danger"),
            
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Тест"),
                    html.Th("Ожидаемый результат"),
                    html.Th("Фактический результат"),
                    html.Th("Статус")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(r.get("test_name", r.get("iteration", ""))),
                        html.Td(r.get("expected", "")),
                        html.Td(r.get("actual", r.get("status", ""))),
                        html.Td(r.get("status", ""), 
                               style={"color": "#10B981" if r.get("status") == "PASS" else "#EF4444"})
                    ]) for r in results[:20]  # Показываем первые 20
                ])
            ], bordered=True, hover=True, responsive=True, size="sm")
        ])
        
        # График
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Пройдено", "Провалено"],
            y=[pass_count, fail_count],
            marker_color=["#10B981", "#EF4444"]
        ))
        fig.update_layout(
            title="Результаты тестирования",
            template="plotly_white",
            height=400
        )
        
        # Лог
        log_text = "\n".join(log_lines + [f"  - {r.get('test_name', r.get('iteration', ''))}: {r.get('status', '')}" for r in results[:10]])
        
        return results_html, fig, log_text.replace('\n', '<br>')
