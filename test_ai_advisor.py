from modules.ai_advisor import create_ai_advisor_panel

# Тестируем
panel = create_ai_advisor_panel(
    vendor="Радиус-Сервис",
    sand_pct=0.6,
    temp_c=105,
    mud_type="Полимерный",
    wob=14.0,
    vibration_g=3.2,
    remaining_hours=120.0
)

print("✅ ИИ-советник создан успешно!")
print(f"Тип: {type(panel)}")
