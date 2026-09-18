"""
ФОНОВЫЙ МОНИТОРИНГ И АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ
Периодическая проверка моделей в фоне с алертами
"""
import time
import threading
from datetime import datetime
from pathlib import Path
import json

class BackgroundMonitor:
    """
    Фоновый мониторинг моделей с периодическим тестированием
    """
    
    def __init__(self, interval_minutes: int = 60):
        self.interval = interval_minutes * 60  # в секундах
        self.is_running = False
        self.log_file = Path("data/background_monitor_log.json")
        self.alerts = []
    
    def start(self):
        """Запуск фонового мониторинга"""
        self.is_running = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
    
    def stop(self):
        """Остановка мониторинга"""
        self.is_running = False
    
    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                # Запуск легких тестов
                self._run_quick_tests()
                
                # Проверка алертов
                self._check_alerts()
                
                # Ожидание следующего цикла
                time.sleep(self.interval)
                
            except Exception as e:
                self._log_error(f"Ошибка в фоновом мониторинге: {str(e)}")
    
    def _run_quick_tests(self):
        """Быстрые тесты для фонового мониторинга"""
        from modules.stress_testing import StressTester
        
        tester = StressTester()
        
        # Запуск граничных тестов для всех модулей
        for module in ["umk_torque", "mud_density", "vzd_wear"]:
            results = tester.run_boundary_tests(module)
            
            # Проверка на провалы
            failed = [r for r in results if r.get("status") == "FAIL"]
            if failed:
                self._create_alert(
                    level="WARNING",
                    message=f"Провалены тесты для модуля {module}: {len(failed)} из {len(results)}",
                    details=failed
                )
    
    def _check_alerts(self):
        """Проверка и обработка алертов"""
        # Здесь можно добавить отправку уведомлений (email, Telegram и т.д.)
        pass
    
    def _create_alert(self, level: str, message: str, details: list = None):
        """Создание алерта"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "details": details
        }
        
        self.alerts.append(alert)
        self._log_alert(alert)
    
    def _log_alert(self, alert: dict):
        """Логирование алерта"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + '\n')
    
    def _log_error(self, error: str):
        """Логирование ошибки"""
        error_log = Path("data/background_monitor_errors.log")
        error_log.parent.mkdir(parents=True, exist_ok=True)
        
        with open(error_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] {error}\n")


# Глобальный экземпляр мониторинга
monitor = BackgroundMonitor(interval_minutes=60)
