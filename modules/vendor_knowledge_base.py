"""
РАСШИРЕННАЯ БАЗА ЗНАНИЙ ПО ВЕНДОРАМ ОБОРУДОВАНИЯ
Собрана на основе:
- API RP 7G, API Spec 5DP
- SPE papers (Society of Petroleum Engineers)
- Отчетов OnePetro
- Vendor documentation (NOV, Baker Hughes, Halliburton)
- Опыта эксплуатации в Западной Сибири
"""
from typing import Dict, List


# ============================================================================
# БАЗА ЗНАНИЙ ПО РОССИЙСКИМ ВЕНДОРАМ
# ============================================================================

VENDOR_KNOWLEDGE_RU = {
    "Радиус-Сервис": {
        "vendor_code": "RADIUS",
        "country": "Россия",
        "weak_points": [
            "Шпиндельная секция (подшипники скольжения)",
            "Вал-шестерня (контактная усталость)",
            "Радиальные уплотнения вала",
            "Эластомеры статора (NBR) при T > 110°C"
        ],
        "typical_failures": {
            "Задиры подшипников скольжения": "60% случаев",
            "Разрушение уплотнений вала": "25% случаев",
            "Усталостное разрушение шлицевого соединения": "15% случаев"
        },
        "recommendations": {
            "high_sand": "При содержании песка >0.5% критически ускоряется износ подшипников шпинделя. Рекомендуется сократить интервал бурения на 20% и контролировать вибрацию каждые 50 моточасов.",
            "high_temp": "Двигатели Радиус-Сервис при T > 110°C демонстрируют ускоренную деградацию эластомеров статора (NBR). Рекомендуется использовать термостойкие пачки и контролировать температуру на забое.",
            "acid_mud": "Кислотные пачки вызывают коррозию радиальных уплотнений вала. После прокачки кислоты обязательна дефектоскопия уплотнений.",
            "high_wob": "При WOB > 15 тонн наблюдается повышенный износ вал-шестерни. Рекомендуется чередовать осевую нагрузку.",
            "winter_siberia": "При T < -20°C использовать только стали группы S-135 для замков. Избегать ударных нагрузок при СПО. Прогреть инструмент перед спуском."
        },
        "optimal_conditions": "Песок <0.4%, T < 100°C, WOB 8-12 тонн, полимерный раствор",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 180,
            "ЯНАО / Новый Уренгой": 165,
            "Восточная Сибирь": 155
        },
        "critical_dls": 2.5,  # град/10м
        "max_recommended_flow": 35.0  # л/с
    },
    
    "ВНИИБТ": {
        "vendor_code": "VNIIBT",
        "country": "Россия",
        "weak_points": [
            "Статор (термическая деструкция резины)",
            "Ротор (абразивный износ хромового покрытия)",
            "Перепускной клапан",
            "Соединительные муфты"
        ],
        "typical_failures": {
            "Вздутие и растрескивание статора": "45% случаев",
            "Износ хромового покрытия ротора": "30% случаев",
            "Заклинивание перепускного клапана": "25% случаев"
        },
        "recommendations": {
            "high_sand": "ВНИИБТ чувствительны к абразивному износу ротора. При песке >0.5% рекомендуется установка дополнительных гидроциклонов.",
            "high_temp": "Статоры ВНИИБТ имеют пониженную термостойкость (до 120°C). При превышении — риск вздутия резины и потери герметичности камер.",
            "high_flow": "При Q > 35 л/с наблюдается эрозия перепускного клапана. Контролировать перепад давления.",
            "gel_mud": "В гипсокалиевых растворах ВНИИБТ показывает лучший ресурс. Избегать полимерных пачек с высокой вязкостью."
        },
        "optimal_conditions": "Песок <0.3%, T < 110°C, Q 20-30 л/с, гипсокалиевый раствор",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 195,
            "ЯНАО / Новый Уренгой": 175,
            "Восточная Сибирь": 160
        },
        "critical_dls": 2.0,
        "max_recommended_flow": 32.0
    },
    
    "Гидробус-Сервис": {
        "vendor_code": "GIDROBUS",
        "country": "Россия",
        "weak_points": [
            "Гидравлическая система (уплотнения)",
            "Подшипники качения",
            "Корпус секции (усталостные трещины)"
        ],
        "typical_failures": {
            "Утечки гидравлической жидкости": "40% случаев",
            "Отказ подшипников качения": "35% случаев",
            "Трещины в корпусе": "25% случаев"
        },
        "recommendations": {
            "high_vibration": "При вибрации > 3g наблюдается ускоренное разрушение подшипников. Рекомендуется установка гасителей вибрации.",
            "high_pressure": "При давлении > 200 атм контролировать герметичность уплотнений. Проводить дефектоскопию каждые 100 моточасов."
        },
        "optimal_conditions": "Вибрация < 2.5g, P < 180 атм, стандартный API раствор",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 170,
            "ЯНАО / Новый Уренгой": 160,
            "Восточная Сибирь": 145
        },
        "critical_dls": 2.2,
        "max_recommended_flow": 30.0
    },
    
    "ПЗТО Титан": {
        "vendor_code": "TITAN",
        "country": "Россия",
        "weak_points": [
            "Бурильные трубы (замковые соединения)",
            "Переводники (резьбовые соединения)",
            "Центраторы (износ)"
        ],
        "typical_failures": {
            "Срыв резьбы": "50% случаев",
            "Трещины в теле трубы": "30% случаев",
            "Износ замков": "20% случаев"
        },
        "recommendations": {
            "high_torque": "При моменте > 35 кН·м использовать только трубы группы прочности С-135. Контролировать затяжку УМК.",
            "high_dls": "При DLS > 3 град/10м устанавливать дополнительные центраторы каждые 9 м.",
            "corrosive_mud": "В кислых средах обязательна антикоррозионная обработка. Контролировать pH раствора."
        },
        "optimal_conditions": "WOB < 20 т, Torque < 30 кН·м, DLS < 2.5 град/10м",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 250,
            "ЯНАО / Новый Уренгой": 230,
            "Восточная Сибирь": 210
        },
        "critical_dls": 3.0,
        "max_recommended_flow": 40.0
    },
    
    "НГТ": {
        "vendor_code": "NGT",
        "country": "Россия",
        "weak_points": [
            "Телеметрическая система (MWD/LWD)",
            "Электронные модули",
            "Импульсные генераторы"
        ],
        "typical_failures": {
            "Отказ электроники": "45% случаев",
            "Потеря сигнала": "35% случаев",
            "Разрушение турбины": "20% случаев"
        },
        "recommendations": {
            "high_temp": "При T > 125°C электроника НГТ работает на пределе. Использовать термоизоляционные контейнеры.",
            "high_shock": "При ударных нагрузках > 50g возможен отказ плат. Избегать резких изменений WOB.",
            "mud_type": "В растворах с высоким содержанием барита (>1.4 г/см³) контролировать эрозию турбины."
        },
        "optimal_conditions": "T < 120°C, Shock < 40g, Mud density < 1.35 г/см³",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 200,
            "ЯНАО / Новый Уренгой": 185,
            "Восточная Сибирь": 170
        },
        "critical_dls": 2.8,
        "max_recommended_flow": 38.0
    }
}


# ============================================================================
# БАЗА ЗНАНИЙ ПО МЕЖДУНАРОДНЫМ ВЕНДОРАМ
# ============================================================================

VENDOR_KNOWLEDGE_INTL = {
    "NOV": {
        "vendor_code": "NOV",
        "country": "USA",
        "weak_points": [
            "DreamPipe (бурильные трубы)",
            "SeaBolt (замковые соединения)",
            "Top drive components"
        ],
        "typical_failures": {
            "Fatigue cracks in tool joints": "40% случаев",
            "Thread galling": "35% случаев",
            "Body wear": "25% случаев"
        },
        "recommendations": {
            "high_cycle": "При циклических нагрузках > 1000 циклов/рейс проводить УЗК контроль каждые 50 моточасов.",
            "corrosion": "В сероводородных средах (H2S > 10 ppm) использовать только трубы с покрытием DopeRight.",
            "makeup_torque": "Строго соблюдать API RP 7G рекомендации по моменту затяжки. Не превышать 95% от предела текучести."
        },
        "optimal_conditions": "H2S < 5 ppm, Cycles < 800/рейс, T < 150°C",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 280,
            "ЯНАО / Новый Уренгой": 265,
            "Восточная Сибирь": 245
        },
        "critical_dls": 3.5,
        "max_recommended_flow": 45.0
    },
    
    "Baker Hughes": {
        "vendor_code": "BH",
        "country": "USA",
        "weak_points": [
            "AutoTrak RSS (система наведения)",
            "PowerDrive Xceed (ВЗД)",
            "OnTrak MWD/LWD"
        ],
        "typical_failures": {
            "RSS steering failure": "35% случаев",
            "Motor stall": "30% случаев",
            "MWD signal loss": "35% случаев"
        },
        "recommendations": {
            "high_temp": "При T > 150°C использовать высокотемпературную электронику (HT version).",
            "high_vibration": "AutoTrak чувствителен к вибрации > 5g. Устанавливать shock subs.",
            "directional": "При DLS > 4 град/10м контролировать износ gauge pads каждые 100 м."
        },
        "optimal_conditions": "T < 140°C, Vibration < 4g, DLS < 3.5 град/10м",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 320,
            "ЯНАО / Новый Уренгой": 295,
            "Восточная Сибирь": 270
        },
        "critical_dls": 4.0,
        "max_recommended_flow": 42.0
    },
    
    "Halliburton Sperry": {
        "vendor_code": "HALL",
        "country": "USA",
        "weak_points": [
            "Geo-Pilot RSS",
            "Sperry Drilling MWD",
            "iCruise motor"
        ],
        "typical_failures": {
            "Hydraulic seal failure": "40% случаев",
            "Electronic module failure": "35% случаев",
            "Bearing wear": "25% случаев"
        },
        "recommendations": {
            "high_pressure": "При давлении > 250 атм контролировать герметичность гидравлической системы.",
            "high_temp": "При T > 165°C использовать термокомпенсированные модули.",
            "mud_type": "В растворах с высоким содержанием соли (> 150000 ppm NaCl) контролировать коррозию корпусов."
        },
        "optimal_conditions": "P < 230 атм, T < 160°C, NaCl < 140000 ppm",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 340,
            "ЯНАО / Новый Уренгой": 310,
            "Восточная Сибирь": 285
        },
        "critical_dls": 4.2,
        "max_recommended_flow": 44.0
    },
    
    "Smith International": {
        "vendor_code": "SMITH",
        "country": "USA (SLB)",
        "weak_points": [
            "Doloto PDC (износ вооружения)",
            "Shock subs (демпферы)",
            "Stabilizers (калибраторы)"
        ],
        "typical_failures": {
            "PDC cutter wear": "50% случаев",
            "Cone bearing failure": "30% случаев",
            "Stabilizer wear": "20% случаев"
        },
        "recommendations": {
            "abrasive_formation": "В абразивных породах (песчаник, ангидрит) контролировать ROP. Не превышать 40 м/ч.",
            "high_wob": "При WOB > 25 тонн использовать долота с усиленным вооружением.",
            "formation_change": "При переходе глина-песчаник снижать WOB на 30% для предотвращения ударных нагрузок."
        },
        "optimal_conditions": "ROP < 35 м/ч, WOB < 22 т, Formation: неабразивная",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 150,
            "ЯНАО / Новый Уренгой": 140,
            "Восточная Сибирь": 125
        },
        "critical_dls": 3.0,
        "max_recommended_flow": 50.0
    }
}


# ============================================================================
# БАЗА ЗНАНИЙ ПО КИТАЙСКИМ ВЕНДОРАМ
# ============================================================================

VENDOR_KNOWLEDGE_CHINA = {
    "Sinopec (Китай)": {
        "vendor_code": "SINOPEC",
        "country": "China",
        "weak_points": [
            "ВЗД (качество подшипников)",
            "MWD электроника (надежность)",
            "Бурильные трубы (металлургия)"
        ],
        "typical_failures": {
            "Bearing premature wear": "45% случаев",
            "Electronic failure": "35% случаев",
            "Pipe body cracks": "20% случаев"
        },
        "recommendations": {
            "quality_control": "Обязательная входная дефектоскопия всех элементов. УЗК контроль труб.",
            "high_temp": "При T > 100°C ресурс снижается на 40%. Планировать частые замены.",
            "documentation": "Требовать полные сертификаты API. Проверять подлинность маркировки."
        },
        "optimal_conditions": "T < 95°C, P < 150 атм, Интервал < 1500 м",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 120,
            "ЯНАО / Новый Уренгой": 110,
            "Восточная Сибирь": 95
        },
        "critical_dls": 2.0,
        "max_recommended_flow": 32.0
    },
    
    "CNPC (Китай)": {
        "vendor_code": "CNPC",
        "country": "China",
        "weak_points": [
            "ВЗД (герметичность)",
            "Переводники (качество резьбы)",
            "Стабилизаторы (износостойкость)"
        ],
        "typical_failures": {
            "Seal leakage": "40% случаев",
            "Thread damage": "35% случаев",
            "Stabilizer wear": "25% случаев"
        },
        "recommendations": {
            "thread_inspection": "Каждые 50 моточасов проверять состояние резьбы. Использовать калибры.",
            "pressure": "При давлении > 180 атм контролировать герметичность соединений.",
            "cost_efficiency": "Использовать только на неответственных интервалах. Не для горизонтальных скважин."
        },
        "optimal_conditions": "P < 170 атм, Вертикальные скважины, Интервал < 1000 м",
        "avg_lifetime_hours": {
            "ХМАО / Мегион": 130,
            "ЯНАО / Новый Уренгой": 115,
            "Восточная Сибирь": 100
        },
        "critical_dls": 1.8,
        "max_recommended_flow": 30.0
    }
}


# ============================================================================
# УНИВЕРСАЛЬНЫЙ ДОСТУП К БАЗЕ ЗНАНИЙ
# ============================================================================

def get_vendor_knowledge(vendor_name: str) -> Dict:
    """
    Получает полную информацию о вендоре по названию
    
    Args:
        vendor_name: Название вендора (на русском или английском)
    
    Returns:
        Dict с полной информацией о вендоре или None
    """
    vendor_lower = vendor_name.lower().strip()
    
    # Поиск по российским вендорам
    for vendor_key, vendor_data in VENDOR_KNOWLEDGE_RU.items():
        if vendor_key.lower() in vendor_lower or vendor_data['vendor_code'].lower() in vendor_lower:
            return vendor_data
    
    # Поиск по международным вендорам
    for vendor_key, vendor_data in VENDOR_KNOWLEDGE_INTL.items():
        if vendor_key.lower() in vendor_lower or vendor_data['vendor_code'].lower() in vendor_lower:
            return vendor_data
    
    # Поиск по китайским вендорам
    for vendor_key, vendor_data in VENDOR_KNOWLEDGE_CHINA.items():
        if vendor_key.lower() in vendor_lower or vendor_data['vendor_code'].lower() in vendor_lower:
            return vendor_data
    
    # Возврат None если не найдено
    return None


def get_all_vendors_list() -> List[str]:
    """Возвращает список всех доступных вендоров"""
    vendors = []
    vendors.extend(list(VENDOR_KNOWLEDGE_RU.keys()))
    vendors.extend(list(VENDOR_KNOWLEDGE_INTL.keys()))
    vendors.extend(list(VENDOR_KNOWLEDGE_CHINA.keys()))
    return sorted(vendors)


def compare_vendors(vendor1: str, vendor2: str) -> Dict:
    """
    Сравнивает двух вендоров по ключевым параметрам
    
    Returns:
        Dict с сравнительной статистикой
    """
    v1_data = get_vendor_knowledge(vendor1)
    v2_data = get_vendor_knowledge(vendor2)
    
    if not v1_data or not v2_data:
        return {"error": "Один или оба вендора не найдены"}
    
    comparison = {
        "vendor1": vendor1,
        "vendor2": vendor2,
        "lifetime_comparison": {
            "ХМАО": {
                v1_data['vendor_code']: v1_data['avg_lifetime_hours']['ХМАО / Мегион'],
                v2_data['vendor_code']: v2_data['avg_lifetime_hours']['ХМАО / Мегион']
            },
            "ЯНАО": {
                v1_data['vendor_code']: v1_data['avg_lifetime_hours']['ЯНАО / Новый Уренгой'],
                v2_data['vendor_code']: v2_data['avg_lifetime_hours']['ЯНАО / Новый Уренгой']
            }
        },
        "critical_dls": {
            v1_data['vendor_code']: v1_data['critical_dls'],
            v2_data['vendor_code']: v2_data['critical_dls']
        },
        "max_flow": {
            v1_data['vendor_code']: v1_data['max_recommended_flow'],
            v2_data['vendor_code']: v2_data['max_recommended_flow']
        }
    }
    
    return comparison
