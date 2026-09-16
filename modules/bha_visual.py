"""
МОДУЛЬ ВИЗУАЛИЗАЦИИ КНБК (PLOTLY)
Рисует интерактивную 2D-схему компоновки с цветовой индикацией стыков.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Пример данных (в будущем будет браться из DataBridge после входного контроля)
bha_elements = [
    {"name": "ТБТ-172", "length": 9.0, "od": 172.0, "status": "OK", "sn": "ТБТ-001"},
    {"name": "Переводник 172/165", "length": 1.5, "od": 172.0, "status": "OK", "sn": "ПП-045"},
    {"name": "НУБТ-165", "length": 9.0, "od": 165.0, "status": "OK", "sn": "НУБТ-112"},
    {"name": "УЗС-165", "length": 3.0, "od": 165.0, "status": "OK", "sn": "УЗС-009"},
    {"name": "ВЗД-172", "length": 8.5, "od": 172.0, "status": "CRIT", "sn": "ВЗД-6677"}, # Критический элемент
]

def create_bha_visualization():
    """Создает фигуру Plotly со схемой КНБК"""
    fig = go.Figure()
    
    current_x = 0
    gap = 0.5 # Расстояние между элементами (визуальный разрыв)
    
    for i, el in enumerate(bha_elements):
        # Цвет цилиндра в зависимости от статуса
        color = "#10B981" if el["status"] == "OK" else "#EF4444" # Зеленый или Красный
        
        # Рисуем цилиндр (прямоугольник с закругленными краями через shape)
        fig.add_shape(
            type="rect",
            x0=current_x, y0=-el["od"]/2, 
            x1=current_x + el["length"], y1=el["od"]/2,
            line=dict(color="#334155", width=2),
            fillcolor=color,
            opacity=0.8,
        )
        
        # Добавляем текстовую метку НАД цилиндром
        fig.add_annotation(
            x=current_x + el["length"]/2, 
            y=el["od"]/2 + 15,
            text=f"<b>{el['name']}</b><br>S/N: {el['sn']}",
            showarrow=False,
            font=dict(size=11, color="#0f172a"),
            align="center"
        )
        
        # Добавляем метку ПОД цилиндром (статус СМК)
        status_text = "ОК" if el["status"] == "OK" else "КРИТ"
        status_color = "#10B981" if el["status"] == "OK" else "#EF4444"
        fig.add_annotation(
            x=current_x + el["length"]/2, 
            y=-el["od"]/2 - 15,
            text=f"<b>{status_text}</b>",
            showarrow=False,
            font=dict(size=12, color=status_color, family="Arial Black")
        )

        # Рисуем стык (перепад диаметров) между элементами
        if i < len(bha_elements) - 1:
            next_el = bha_elements[i+1]
            delta_d = abs(el["od"] - next_el["od"])
            
            # Если перепад больше 10 мм - рисуем красное предупреждение
            if delta_d > 10.0:
                fig.add_annotation(
                    x=current_x + el["length"] + gap/2,
                    y=max(el["od"], next_el["od"])/2 + 30,
                    text=f"⚠️ ΔD={delta_d:.1f}мм",
                    showarrow=True,
                    arrowhead=2,
                    ax=0, ay=-20,
                    font=dict(color="#EF4444", size=12, weight="bold"),
                    bordercolor="#EF4444",
                    borderwidth=1,
                    borderpad=4,
                    bgcolor="#FEF2F2"
                )
            current_x += el["length"] + gap

    # Настройка внешнего вида графика
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title="Длина КНБК, м"),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title="Диаметр, мм"),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#f8fafc",
        hovermode="x unified",
        title=dict(text="Топологическая схема КНБК (Визуальный контроль)", x=0.5, font=dict(size=16, color="#0f172a"))
    )
    
    # Добавляем невидимые scatter-точки для красивых тултипов при наведении
    for i, el in enumerate(bha_elements):
        fig.add_trace(go.Scatter(
            x=[current_x/2], # Примерное позиционирование для тултипа
            y=[0],
            mode='markers',
            marker=dict(size=0), # Невидимая точка
            hoverinfo='text',
            hovertext=f"<b>{el['name']}</b><br>OD: {el['od']} мм<br>Статус: {el['status']}",
            showlegend=False
        ))

    return fig
