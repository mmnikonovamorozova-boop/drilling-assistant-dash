"""
COMPLIANCE ENGINE v2.0
Централизованное управление нормативными требованиями:
- Отраслевые стандарты (СТО ИНТИ, API, ГОСТ, ISO)
- Корпоративные технические регламенты (ТК)
- Локальные нормативные документы (ЛНД) дочерних обществ (включая Волго-Урал)

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
    client_hierarchy: str  # "Роснефть", "Татнефть", "Башнефть", etc.
    description: str = ""
    mandatory: bool = True
    effective_date: str = ""
    superseded_by: str = None


class ComplianceEngine:
    """Основной движок управления комплаенсом"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.rules_file = self.data_dir / "compliance_rules.json"
        self.excel_file = self.data_dir / "compliance_rules.xlsx"
        self.rules_cache: Dict[str, ComplianceRule] = {}
        self.load_rules()
    
    def load_rules(self):
        if self.rules_file.exists():
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.rules_cache = {rule_id: ComplianceRule(**rule_data) for rule_id, rule_data in data.items()}
        else:
            self._create_default_rules()
            self.save_rules()
    
    def save_rules(self):
        data = {
            rule_id: {
                'rule_id': rule.rule_id, 'category': rule.category, 'parameter': rule.parameter,
                'value': rule.value, 'unit': rule.unit, 'standard_source': rule.standard_source,
                'priority': rule.priority, 'client_hierarchy': rule.client_hierarchy,
                'description': rule.description, 'mandatory': rule.mandatory,
                'effective_date': rule.effective_date, 'superseded_by': rule.superseded_by
            }
            for rule_id, rule in self.rules_cache.items()
        }
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._export_to_excel()
    
    def _create_default_rules(self):
        # =========================================================================
        # LEVEL 1: ОТРАСЛЕВЫЕ СТАНДАРТЫ
        # =========================================================================
        self.rules_cache['INTI_S100_3_sand'] = ComplianceRule(
            rule_id='INTI_S100_3_sand', category='sand_limit', parameter='max_sand_content',
            value=0.5, unit='%', standard_source='СТО ИНТИ S.100.3', priority=1,
            client_hierarchy='*', description='Базовый лимит содержания песка по СТО ИНТИ',
            mandatory=True, effective_date='2024-01-01'
        )
        self.rules_cache['INTI_S100_3_ecd'] = ComplianceRule(
            rule_id='INTI_S100_3_ecd', category='ecd_buffer', parameter='min_ecd_buffer',
            value=0.025, unit='г/см³', standard_source='СТО ИНТИ S.100.3', priority=1,
            client_hierarchy='*', description='Минимальный буфер ЭЦП до ГРП',
            mandatory=True, effective_date='2024-01-01'
        )
        self.rules_cache['INTI_SQS7_vzd_mpi'] = ComplianceRule(
            rule_id='INTI_SQS7_vzd_mpi', category='mpi_hours', parameter='vzd_default_mpi',
            value=200.0, unit='часов', standard_source='СТО ИНТИ S.QS.7', priority=1,
            client_hierarchy='*', description='Стандартный межповерочный интервал ВЗД',
            mandatory=True, effective_date='2024-01-01'
        )
        
        # =========================================================================
        # LEVEL 2: КОРПОРАТИВНЫЕ ТЕХНИЧЕСКИЕ РЕГЛАМЕНТЫ
        # =========================================================================
        self.rules_cache['RN_sand_limit'] = ComplianceRule(
            rule_id='RN_sand_limit', category='sand_limit', parameter='max_sand_content',
            value=0.5, unit='%', standard_source='ТК Роснефть 01-2024', priority=2,
            client_hierarchy='Роснефть', description='Корпоративный лимит песка Роснефть',
            mandatory=True, effective_date='2024-01-01'
        )
        self.rules_cache['GP_sand_limit'] = ComplianceRule(
            rule_id='GP_sand_limit', category='sand_limit', parameter='max_sand_content',
            value=0.4, unit='%', standard_source='СТ Газпром нефть 2-2024', priority=2,
            client_hierarchy='Газпром нефть', description='Ужесточенный лимит песка для Газпром нефть',
            mandatory=True, effective_date='2024-01-01'
        )
        self.rules_cache['LK_sand_limit'] = ComplianceRule(
            rule_id='LK_sand_limit', category='sand_limit', parameter='max_sand_content',
            value=0.5, unit='%', standard_source='СТ ЛУКОЙЛ 3-2024', priority=2,
            client_hierarchy='ЛУКОЙЛ', description='Лимит песка ЛУКОЙЛ',
            mandatory=True, effective_date='2024-01-01'
        )
        
        # СПЕЦИФИКА ВОЛГО-УРАЛА
        self.rules_cache['TAT_sand_limit'] = ComplianceRule(
            rule_id='TAT_sand_limit', category='sand_limit', parameter='max_sand_content',
            value=0.3, unit='%', standard_source='СТО Татнефть 01-2024', priority=2,
            client_hierarchy='Татнефть', description='Ужесточенный лимит песка для скважин Татнефти',
            mandatory=True, effective_date='2024-01-01'
        )
        
        # =========================================================================
        # LEVEL 3: ЛОКАЛЬНЫЕ НД ДОЧЕРНИХ ОБЩЕСТВ
        # =========================================================================
        self.rules_cache['RN-YUG_sand_limit'] = ComplianceRule(
            rule_id='RN-YUG_sand_limit', category='sand_limit', parameter='max_sand_content',
            value=0.45, unit='%', standard_source='ЛНД РН-Юганскнефтегаз 05-2024', priority=3,
            client_hierarchy='РН-Юганскнефтегаз', description='Ужесточенный локальный лимит для Юганска',
            mandatory=True, effective_date='2024-03-01'
        )
        self.rules_cache['BASH_sand_limit'] = ComplianceRule(
            rule_id='BASH_sand_limit', category='sand_limit', parameter='max_sand_content',
            value=0.4, unit='%', standard_source='ЛНД Башнефть 02-2024', priority=3,
            client_hierarchy='Башнефть', description='Локальный лимит песка Башнефть (Волго-Урал)',
            mandatory=True, effective_date='2024-02-01'
        )

    def get_limit(self, client_name: str, category: str, parameter: str, default_value: float = None) -> Tuple[float, str, str]:
        # 1. Ищем точное совпадение по клиенту (Level 3)
        for rule in self.rules_cache.values():
            if rule.category == category and rule.parameter == parameter and rule.client_hierarchy == client_name:
                return rule.value, rule.unit, rule.standard_source
        
        # 2. Ищем правило母公司 (Level 2)
        parent = self._get_parent_company(client_name)
        if parent:
            for rule in self.rules_cache.values():
                if rule.category == category and rule.parameter == parameter and rule.client_hierarchy == parent and rule.priority == 2:
                    return rule.value, rule.unit, rule.standard_source
        
        # 3. Ищем отраслевой стандарт (Level 1)
        for rule in self.rules_cache.values():
            if rule.category == category and rule.parameter == parameter and rule.client_hierarchy == '*' and rule.priority == 1:
                return rule.value, rule.unit, rule.standard_source
        
        return default_value, "н/д", "Значение по умолчанию"
    
    def _get_parent_company(self, client_name: str) -> Optional[str]:
        """Определение материнской компании (холдинга) для дочернего общества"""
        parent_map = {
            # Западная Сибирь
            "РН-Юганскнефтегаз": "Роснефть",
            "РН-Ванкор": "Роснефть",
            "Газпром добыча Ноябрьск": "Газпром нефть",
            "Газпром добыча Уренгой": "Газпром нефть",
            
            # Волго-Урал (ДОБАВЛЕНО)
            "Татнефть": "Татнефть",
            "Башнефть": "Роснефть",
            "Удмуртнефть": "Роснефть",
            "ЛУКОЙЛ-Пермь": "ЛУКОЙЛ",
            "ЛУКОЙЛ-Коми": "ЛУКОЙЛ",
            "РуссНефть": "РуссНефть",
            
            # Восточная Сибирь
            "Верхнечонскнефтегаз": "Роснефть",
        }
        return parent_map.get(client_name)
    
    def _export_to_excel(self):
        data = [{
            'Rule_ID': rule.rule_id, 'Категория': rule.category, 'Параметр': rule.parameter,
            'Значение': rule.value, 'Ед.изм.': rule.unit, 'Источник': rule.standard_source,
            'Приоритет': rule.priority, 'Заказчик': rule.client_hierarchy, 'Описание': rule.description,
            'Обязательно': 'Да' if rule.mandatory else 'Нет', 'Дата вступления': rule.effective_date
        } for rule in self.rules_cache.values()]
        pd.DataFrame(data).to_excel(self.excel_file, index=False, engine='openpyxl')


_compliance_engine_instance = None
def get_compliance_engine() -> ComplianceEngine:
    global _compliance_engine_instance
    if _compliance_engine_instance is None:
        _compliance_engine_instance = ComplianceEngine()
    return _compliance_engine_instance
