"""
ЛОКАЛЬНЫЙ ИИ-ПАРСЕР ДОКУМЕНТОВ
Работает полностью оффлайн, извлекает лимиты и требования из PDF/сканов
"""
import os
import json
import re
from pathlib import Path
import camelot  # Для таблиц
import fitz  # PyMuPDF для текста
from paddleocr import PaddleOCR  # Для сканов
from openai import OpenAI  # Для работы с Ollama

class LocalDocParser:
    def __init__(self):
        # Инициализация OCR (русский + английский)
        self.ocr = PaddleOCR(lang='ru', use_gpu=False)  # use_gpu=True если есть NVIDIA
        
        # Подключение к локальной Ollama
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="not-needed"
        )
        self.model = "qwen2.5:7b"  # или "qwen2.5:14b"
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Извлекает текст из PDF (обычный или скан)"""
        doc = fitz.open(pdf_path)
        full_text = ""
        
        for page in doc:
            # Пробуем извлечь обычный текст
            text = page.get_text()
            
            if len(text.strip()) < 50:  # Если мало текста — это скан
                # Конвертируем страницу в изображение и распознаем OCR
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                result = self.ocr.ocr(img_data, cls=True)
                
                text = ""
                if result and result[0]:
                    for line in result[0]:
                        text += line[1][0] + "\n"
            
            full_text += text + "\n"
        
        return full_text
    
    def extract_tables_from_pdf(self, pdf_path: str) -> list:
        """Извлекает таблицы из PDF"""
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        tables_data = []
        for i, table in enumerate(tables):
            df = table.df
            tables_data.append({
                "table_index": i,
                "data": df.to_dict('records'),
                "columns": list(df.columns)
            })
        
        return tables_data
    
    def parse_requirements(self, text: str, tables: list) -> dict:
        """
        Использует ИИ для извлечения требований и лимитов
        Возвращает структурированный JSON
        """
        # Формируем промпт для ИИ
        prompt = f"""
Ты — эксперт по анализу технических документов (ТЗ, договоры на бурение).
Твоя задача: извлечь все технологические лимиты и требования в формате JSON.

Текст документа:
{text}

Таблицы из документа:
{json.dumps(tables, ensure_ascii=False, indent=2)}

Извлеки следующие параметры (если они есть):
1. Лимиты по интенсивности искривления (DLS, град/10м)
2. Лимиты по содержанию песка в растворе (%)
3. Лимиты по буферу ЭЦП (г/см³)
4. Межповерочный интервал ВЗД (часы)
5. Любые другие числовые ограничения

Верни ТОЛЬКО JSON в формате:
{{
  "rules": [
    {{
      "rule_id": "уникальный_id",
      "category": "dls_limit или sand_limit или ecd_buffer или mpi_hours",
      "parameter": "max_dls или max_sand_content и т.д.",
      "value": 3.0,
      "unit": "°/10м или % или г/см³ или часов",
      "description": "описание требования",
      "mandatory": true
    }}
  ]
}}

Если параметр не найден — не включай его в результат.
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Минимум креатива, максимум точности
        )
        
        # Парсим ответ ИИ
        try:
            result_json = json.loads(response.choices[0].message.content)
            return result_json
        except:
            # Если ИИ вернул не JSON, пытаемся исправить
            return self._extract_json_fallback(response.choices[0].message.content)
    
    def _extract_json_fallback(self, text: str) -> dict:
        """Резервный парсинг, если ИИ не вернул чистый JSON"""
        # Ищем JSON между { и }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {"rules": []}
    
    def process_document(self, pdf_path: str, client_name: str) -> dict:
        """
        Полный цикл обработки документа
        """
        print(f"📄 Обработка документа: {pdf_path}")
        
        # 1. Извлечение текста
        text = self.extract_text_from_pdf(pdf_path)
        
        # 2. Извлечение таблиц
        tables = self.extract_tables_from_pdf(pdf_path)
        
        # 3. ИИ-анализ
        structured_data = self.parse_requirements(text, tables)
        
        # 4. Добавляем метаданные
        structured_data["metadata"] = {
            "source_file": Path(pdf_path).name,
            "client": client_name,
            "processed_date": datetime.now().isoformat()
        }
        
        return structured_data


# Пример использования
if __name__ == "__main__":
    parser = LocalDocParser()
    
    # Обрабатываем все PDF в папке input_docs
    input_dir = Path("input_docs")
    output_file = Path("data/kb_update.json")
    
    all_rules = {"rules": [], "metadata": {}}
    
    for pdf_file in input_dir.glob("*.pdf"):
        # Определяем заказчика из имени файла (например: "Tatneft_TZ_2024.pdf")
        client_name = pdf_file.stem.split("_")[0]
        
        result = parser.process_document(str(pdf_file), client_name)
        all_rules["rules"].extend(result.get("rules", []))
    
    # Сохраняем результат
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Готово! Загружено {len(all_rules['rules'])} правил в {output_file}")
