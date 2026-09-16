"""
СКВОЗНОЙ ШЛЮЗ ДАННЫХ МЕЖДУ МОДУЛЯМИ
Заменяет st.session_state из Streamlit
"""
import json
from datetime import datetime

class DataBridge:
    """Единое хранилище данных для всех модулей"""
    
    def __init__(self):
        self.data = {
            # Данные авторизации
            'engineer_name': 'Не указано',
            'well_number': 'Не указано',
            'field_name': 'Не указано',
            'bha_number': '1',
            'company_choice': 'Роснефть',
            
            # Данные модуля "Контроль растворов"
            'mud_density': 1.12,
            'sand_content': 0.5,
            'plastic_viscosity': 25.0,
            'yield_stress': 12.0,
            
            # Данные модуля "Виртуальный ротор"
            'vzd_brand': 'Не определен',
            'vzd_limit': 4.5,
            'vzd_hours': 48.0,
            
            # Общие расчетные данные
            'ecd_value': 0.0,
            'risk_index': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def set(self, key, value):
        """Установить значение"""
        self.data[key] = value
        self.data['timestamp'] = datetime.now().isoformat()
    
    def get(self, key, default=None):
        """Получить значение"""
        return self.data.get(key, default)
    
    def get_all(self):
        """Получить все данные"""
        return self.data.copy()
    
    def update_from_dict(self, data_dict):
        """Обновить несколько значений сразу"""
        self.data.update(data_dict)
        self.data['timestamp'] = datetime.now().isoformat()
    
    def to_json(self):
        """Сериализовать в JSON для dcc.Store"""
        return json.dumps(self.data, default=str)
    
    def from_json(self, json_str):
        """Десериализовать из JSON"""
        if json_str:
            self.data.update(json.loads(json_str))
