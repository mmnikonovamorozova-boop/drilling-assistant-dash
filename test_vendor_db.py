"""
Тест расширенной базы знаний по вендорам
"""
from modules.vendor_knowledge_base import (
    get_vendor_knowledge, 
    get_all_vendors_list,
    compare_vendors
)

print("=== ВСЕ ДОСТУПНЫЕ ВЕНДОРЫ ===")
vendors = get_all_vendors_list()
for v in vendors:
    print(f"✓ {v}")

print("\n=== ТЕСТИРОВАНИЕ ПОИСКА ===")
test_vendors = ["Радиус-Сервис", "NOV", "Baker Hughes", "Sinopec"]

for vendor in test_vendors:
    data = get_vendor_knowledge(vendor)
    if data:
        print(f"\n{vendor}:")
        print(f"  Код: {data['vendor_code']}")
        print(f"  Страна: {data['country']}")
        print(f"  Слабые места: {', '.join(data['weak_points'][:2])}...")
        print(f"  Средний ресурс (ХМАО): {data['avg_lifetime_hours']['ХМАО / Мегион']} ч")
    else:
        print(f"❌ {vendor} - НЕ НАЙДЕН")

print("\n=== СРАВНЕНИЕ ВЕНДОРОВ ===")
comparison = compare_vendors("Радиус-Сервис", "Baker Hughes")
if "error" not in comparison:
    print(f"Сравнение: {comparison['vendor1']} vs {comparison['vendor2']}")
    print(f"Ресурс в ХМАО: {comparison['lifetime_comparison']['ХМАО']}")
    print(f"Критический DLS: {comparison['critical_dls']}")

print("\n✅ Тест завершен!")
