"""
COMPLIANCE ENGINE v2.0
Централизованное управление нормативными требованиями:
- Отраслевые стандарты (СТО ИНТИ, API, ГОСТ, ISO)
- Корпоративные технические регламенты (ТК)
- Локальные нормативные документы (ЛНД) дочерних обществ

Архитектура: Наследование правил (Level 1 → Level 2 → Level 3)
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ComplianceRule:
    """Структура одного правила/требования"""
    rule_id: str
    category: str  # "sand_limit", "ecd_buffer", "mpi_hours", etc.
    parameter: str
    value: float
    unit: str
    standard_source: str  # "СТО ИНТИ S.100.3", "API RP 13D", etc.
    priority: int  # 1=Базовый стандарт, 2=Корпоративный, 3=Локальный
    client_hierarchy: str  # "Роснефть", "РН-Юганскнефтегаз", etc.
    description: str = ""
    mandatory: bool = True
    effective_date: str = ""
    superseded_by: str = None  # ID правила, которое заменяет это


@dataclass
class StandardHierarchy:
    """Иерархия стандартов"""
    # Level 1: Отраслевые стандарты
    industry_standards: Dict[str, dict] = field(default_factory=dict)
    
    # Level 2: Корпоративные ТК
    corporate_standards: Dict[str, dict] = field(default_factory=dict)
    
    # Level 3: Локальные НД дочек
    local_standards: Dict[str, dict] = field(default_factory=dict)


class ComplianceEngine:
    """
    Основной движок управления комплаенсом
    
    Поддерживает:
    - Многослойную иерархию стандартов
    - Наследование правил (дочка → мать → отраслевой стандарт)
    - Приоритизацию требований
    - Валидацию параметров
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Пути к файлам
        self.rules_file = self.data_dir / "compliance_rules.json"
        self.standards_file = self.data_dir / "standards_hierarchy.json"
        self.excel_file = self.data_dir / "compliance_rules.xlsx"
        
        # Кэш правил
        self.rules_cache: Dict[str, ComplianceRule] = {}
        self.hierarchy = StandardHierarchy()
        
        # Загрузка правил при инициализации
        self.load_rules()
    
    # =========================================================================
    # ЗАГРУЗКА И СОХРАНЕНИЕ ПРАВИЛ
    # =========================================================================
    
    def load_rules(self):
        """Загрузка правил из JSON или создание дефолтных"""
        if self.rules_file.exists():
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.rules_cache = {
                rule_id: ComplianceRule(**rule_data)
                for rule_id, rule_data in data.items()
            }
        else:
            # Создание дефолтных правил
            self._create_default_rules()
            self.save_rules()
    
    def save_rules(self):
        """Сохранение правил в JSON"""
        data = {
            rule_id: {
                'rule_id': rule.rule_id,
                'category': rule.category,
                'parameter': rule.parameter,
                'value': rule.value,
                'unit': rule.unit,
                'standard_source': rule.standard_source,
                'priority': rule.priority,
                'client_hierarchy': rule.client_hierarchy,
                'description': rule.description,
                'mandatory': rule.mandatory,
                'effective_date': rule.effective_date,
                'superseded_by': rule.superseded_by
            }
            for rule_id, rule in self.rules_cache.items()
        }
        
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Экспорт в Excel для удобства редактирования
        self._export_to_excel()
    
    def _create_default_rules(self):
        """Создание базовых правил по умолчанию"""
        
        # =========================================================================
        # LEVEL 1: ОТРАСЛЕВЫЕ СТАНДАРТЫ (СТО ИНТИ, API, ГОСТ)
        # =========================================================================
        
        # СТО ИНТИ S.100.3 - Контроль буровых растворов
        self.rules_cache['INTI_S100_3_sand'] = ComplianceRule(
            rule_id='INTI_S100_3_sand',
            category='sand_limit',
            parameter='max_sand_content',
            value=0.5,
            unit='%',
            standard_source='СТО ИНТИ S.100.3',
            priority=1,
            client_hierarchy='*',
            description='Базовый лимит содержания песка по СТО ИНТИ',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        self.rules_cache['INTI_S100_3_ecd'] = ComplianceRule(
            rule_id='INTI_S100_3_ecd',
            category='ecd_buffer',
            parameter='min_ecd_buffer',
            value=0.025,
            unit='г/см³',
            standard_source='СТО ИНТИ S.100.3',
            priority=1,
            client_hierarchy='*',
            description='Минимальный буфер ЭЦП до ГРП',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        self.rules_cache['INTI_SQS7_vzd_mpi'] = ComplianceRule(
            rule_id='INTI_SQS7_vzd_mpi',
            category='mpi_hours',
            parameter='vzd_default_mpi',
            value=200.0,
            unit='часов',
            standard_source='СТО ИНТИ S.QS.7',
            priority=1,
            client_hierarchy='*',
            description='Стандартный межповерочный интервал ВЗД',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        # API RP 13D - Гидравлическое моделирование
        self.rules_cache['API_RP13D_rheology'] = ComplianceRule(
            rule_id='API_RP13D_rheology',
            category='rheology_model',
            parameter='default_model',
            value=1.0,  # Herschel-Bulkley
            unit='код модели',
            standard_source='API RP 13D',
            priority=1,
            client_hierarchy='*',
            description='Рекомендуемая реологическая модель',
            mandatory=False,
            effective_date='2023-01-01'
        )
        
        # =========================================================================
        # LEVEL 2: КОРПОРАТИВНЫЕ ТЕХНИЧЕСКИЕ РЕГЛАМЕНТЫ
        # =========================================================================
        
        # Роснефть
        self.rules_cache['RN_sand_limit'] = ComplianceRule(
            rule_id='RN_sand_limit',
            category='sand_limit',
            parameter='max_sand_content',
            value=0.5,
            unit='%',
            standard_source='ТК Роснефть 01-2024',
            priority=2,
            client_hierarchy='Роснефть',
            description='Корпоративный лимит песка Роснефть',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        self.rules_cache['RN_ecd_buffer'] = ComplianceRule(
            rule_id='RN_ecd_buffer',
            category='ecd_buffer',
            parameter='min_ecd_buffer',
            value=0.030,
            unit='г/см³',
            standard_source='ТК Роснефть 01-2024',
            priority=2,
            client_hierarchy='Роснефть',
            description='Увеличенный буфер ЭЦП для Роснефть',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        # Газпром нефть
        self.rules_cache['GP_sand_limit'] = ComplianceRule(
            rule_id='GP_sand_limit',
            category='sand_limit',
            parameter='max_sand_content',
            value=0.4,
            unit='%',
            standard_source='СТ Газпром нефть 2-2024',
            priority=2,
            client_hierarchy='Газпром нефть',
            description='Ужесточенный лимит песка для Газпром нефть',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        self.rules_cache['GP_ecd_buffer'] = ComplianceRule(
            rule_id='GP_ecd_buffer',
            category='ecd_buffer',
            parameter='min_ecd_buffer',
            value=0.020,
            unit='г/см³',
            standard_source='СТ Газпром нефть 2-2024',
            priority=2,
            client_hierarchy='Газпром нефть',
            description='Стандартный буфер ЭЦП',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        # ЛУКОЙЛ
        self.rules_cache['LK_sand_limit'] = ComplianceRule(
            rule_id='LK_sand_limit',
            category='sand_limit',
            parameter='max_sand_content',
            value=0.5,
            unit='%',
            standard_source='СТ ЛУКОЙЛ 3-2024',
            priority=2,
            client_hierarchy='ЛУКОЙЛ',
            description='Лимит песка ЛУКОЙЛ',
            mandatory=True,
            effective_date='2024-01-01'
        )
        
        # =========================================================================
        # LEVEL 3: ЛОКАЛЬНЫЕ НД ДОЧЕРНИХ ОБЩЕСТВ
        # =========================================================================
        
        # РН-Юганскнефтегаз (дочка Роснефти)
        self.rules_cache['RN-YUG_sand_limit'] = ComplianceRule(
            rule_id='RN-YUG_sand_limit',
            category='sand_limit',
            parameter='max_sand_content',
            value=0.45,
            unit='%',
            standard_source='ЛНД РН-Юганскнефтегаз 05-2024',
            priority=3,
            client_hierarchy='РН-Юганскнефтегаз',
            parent_hierarchy='Роснефть',
            description='Ужесточенный локальный лимит для Юганска',
            mandatory=True,
            effective_date='2024-03-01'
        )
        
        # Газпром добыча Ноябрьск (дочка Газпром нефти)
        self.rules_cache['GP-NOY_sand_limit'] = ComplianceRule(
            rule_id='GP-NOY_sand_limit',
            category='sand_limit',
            parameter='max_sand_content',
            value=0.35,
            unit='%',
            standard_source='ЛНД Газпром добыча Ноябрьск',
            priority=3,
            client_hierarchy='Газпром добыча Ноябрьск',
            parent_hierarchy='Газпром нефть',
            description='Сверхжесткий лимит для Ноябрьска',
            mandatory=True,
            effective_date='2024-02-01'
        )
    
    # =========================================================================
    # ОСНОВНЫЕ МЕТОДЫ ПОЛУЧЕНИЯ ПРАВИЛ
    # =========================================================================
    
    def get_limit(self, client_name: str, category: str, parameter: str, 
                  default_value: float = None) -> Tuple[float, str, str]:
        """
        Получение лимита с учетом иерархии
        
        Args:
            client_name: Название заказчика (например, "РН-Юганскнефтегаз")
            category: Категория правила (sand_limit, ecd_buffer, etc.)
            parameter: Конкретный параметр
            default_value: Значение по умолчанию
        
        Returns:
            (value, unit, standard_source) - значение, единица, источник
        """
        # 1. Ищем точное совпадение по клиенту (Level 3 - локальные НД)
        for rule in self.rules_cache.values():
            if (rule.category == category and 
                rule.parameter == parameter and
                rule.client_hierarchy == client_name):
                return rule.value, rule.unit, rule.standard_source
        
        # 2. Ищем правило母公司 (Level 2 - корпоративные ТК)
        parent = self._get_parent_company(client_name)
        if parent:
            for rule in self.rules_cache.values():
                if (rule.category == category and 
                    rule.parameter == parameter and
                    rule.client_hierarchy == parent and
                    rule.priority == 2):
                    return rule.value, rule.unit, rule.standard_source
        
        # 3. Ищем отраслевой стандарт (Level 1)
        for rule in self.rules_cache.values():
            if (rule.category == category and 
                rule.parameter == parameter and
                rule.client_hierarchy == '*' and
                rule.priority == 1):
                return rule.value, rule.unit, rule.standard_source
        
        # 4. Возвращаем дефолтное значение
        return default_value, "н/д", "Значение по умолчанию"
    
    def _get_parent_company(self, client_name: str) -> Optional[str]:
        """Определение母公司 (холдинга) для дочернего общества"""
        parent_map = {
            "РН-Юганскнефтегаз": "Роснефть",
            "РН-Ванкор": "Роснефть",
            "РН-Пурнефтегаз": "Роснефть",
            "Газпром добыча Ноябрьск": "Газпром нефть",
            "Газпром добыча Уренгой": "Газпром нефть",
            "ЛУКОЙЛ-Западная Сибирь": "ЛУКОЙЛ",
            "ЛУКОЙЛ-Коми": "ЛУКОЙЛ",
        }
        return parent_map.get(client_name)
    
    # =========================================================================
    # ВАЛИДАЦИЯ И ПРОВЕРКА КОМПЛАЕНСА
    # =========================================================================
    
    def validate_parameter(self, client_name: str, category: str, 
                          actual_value: float, parameter: str) -> Dict:
        """
        Проверка фактического значения на соответствие требованиям
        
        Args:
            client_name: Заказчик
            category: Категория
            actual_value: Фактическое значение
            parameter: Параметр
        
        Returns:
            Dict с результатом валидации
        """
        limit, unit, source = self.get_limit(client_name, category, parameter)
        
        if limit is None:
            return {
                'status': 'UNKNOWN',
                'message': 'Правило не найдено',
                'limit': None,
                'actual': actual_value
            }
        
        # Для sand_limit: чем меньше, тем лучше
        if category == 'sand_limit':
            is_compliant = actual_value <= limit
            margin = limit - actual_value
        # Для ecd_buffer: чем больше, тем лучше
        elif category == 'ecd_buffer':
            is_compliant = actual_value >= limit
            margin = actual_value - limit
        else:
            # Общий случай
            is_compliant = abs(actual_value - limit) < 0.01
            margin = abs(actual_value - limit)
        
        return {
            'status': 'COMPLIANT' if is_compliant else 'NON_COMPLIANT',
            'message': 'Соответствует' if is_compliant else 'НАРУШЕНИЕ!',
            'limit': limit,
            'actual': actual_value,
            'unit': unit,
            'margin': margin,
            'standard_source': source,
            'client': client_name
        }
    
    # =========================================================================
    # ЭКСПОРТ И ИМПОРТ
    # =========================================================================
    
    def _export_to_excel(self):
        """Экспорт правил в Excel для удобства редактирования"""
        data = []
        for rule in self.rules_cache.values():
            data.append({
                'Rule_ID': rule.rule_id,
                'Категория': rule.category,
                'Параметр': rule.parameter,
                'Значение': rule.value,
                'Ед.изм.': rule.unit,
                'Источник': rule.standard_source,
                'Приоритет': rule.priority,
                'Заказчик': rule.client_hierarchy,
                'Описание': rule.description,
                'Обязательно': 'Да' if rule.mandatory else 'Нет',
                'Дата вступления': rule.effective_date
            })
        
        df = pd.DataFrame(data)
        df.to_excel(self.excel_file, index=False, engine='openpyxl')
    
    def import_from_excel(self, excel_path: str):
        """Импорт правил из Excel (для офисного использования)"""
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        for _, row in df.iterrows():
            rule = ComplianceRule(
                rule_id=str(row['Rule_ID']),
                category=str(row['Категория']),
                parameter=str(row['Параметр']),
                value=float(row['Значение']),
                unit=str(row['Ед.изм.']),
                standard_source=str(row['Источник']),
                priority=int(row['Приоритет']),
                client_hierarchy=str(row['Заказчик']),
                description=str(row.get('Описание', '')),
                mandatory=str(row.get('Обязательно', 'Да')) == 'Да',
                effective_date=str(row.get('Дата вступления', ''))
            )
            self.rules_cache[rule.rule_id] = rule
        
        self.save_rules()
    
    # =========================================================================
    # ОТЧЕТНОСТЬ
    # =========================================================================
    
    def get_compliance_report(self, client_name: str) -> str:
        """Генерация отчета по комплаенсу для заказчика"""
        report_lines = [
            f"ОТЧЕТ ПО КОМПЛАЕНСУ",
            f"Заказчик: {client_name}",
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "=" * 60,
            ""
        ]
        
        # Группируем правила по категориям
        categories = set(rule.category for rule in self.rules_cache.values())
        
        for category in sorted(categories):
            report_lines.append(f"\n{category.upper()}:")
            report_lines.append("-" * 40)
            
            limit, unit, source = self.get_limit(
                client_name, category, 
                self.rules_cache[next(iter(self.rules_cache))].parameter
            )
            
            report_lines.append(f"  Лимит: {limit} {unit}")
            report_lines.append(f"  Источник: {source}")
        
        return "\n".join(report_lines)


# =============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР (Singleton)
# =============================================================================

_compliance_engine_instance = None

def get_compliance_engine() -> ComplianceEngine:
    """Получение глобального экземпляра Compliance Engine"""
    global _compliance_engine_instance
    if _compliance_engine_instance is None:
        _compliance_engine_instance = ComplianceEngine()
    return _compliance_engine_instance
