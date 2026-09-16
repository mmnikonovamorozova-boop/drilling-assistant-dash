"""
ЛОКАЛЬНЫЙ ИИ-ПАРСЕР ТЕХНИЧЕСКИХ ДОКУМЕНТОВ
Извлекает технологические лимиты и требования из PDF (обычных и сканов)
с помощью локальной LLM (Ollama + Qwen2.5).

Использование:
    python tools/local_ai_parser.py                    # Обработать все PDF в data/input_docs/
    python tools/local_ai_parser.py --file doc.pdf     # Обработать один файл
    python tools/local_ai_parser.py --folder /path     # Обработать папку

Требования:
    - Установленная Ollama (https://ollama.ai)
    - Модель: ollama pull qwen2.5:7b
    - pip install -r tools/requirements_parser.txt
"""
import os
import sys
import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Опциональные зависимости — импорт внутри функций для graceful degradation
# import fitz  # PyMuPDF
# import camelot
# from paddleocr import PaddleOCR
# from openai import OpenAI

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('local_ai_parser')


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

DEFAULT_MODEL = "qwen2.5:7b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"  # Фиктивный ключ для совместимости с OpenAI SDK

# Категории, которые мы ищем в документах
TARGET_CATEGORIES = [
    "dls_limit",        # Лимит интенсивности искривления
    "sand_limit",       # Лимит содержания песка
    "ecd_buffer",       # Буфер ЭЦП до ГРП
    "mpi_hours",        # Межповерочный интервал ВЗД
    "mud_density",      # Плотность раствора
    "wob_limit",        # Ограничение WOB
    "temperature_limit" # Температурный лимит
]


# ============================================================================
# КЛАСС ПАРСЕРА
# ============================================================================

class LocalDocParser:
    """
    Парсер технических документов с локальным ИИ.
    Работает полностью оффлайн после первой загрузки модели.
    """
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = None
        self.ocr = None
        self._init_dependencies()
    
    def _init_dependencies(self):
        """Инициализация зависимостей с проверкой доступности"""
        # 1. Ollama клиент
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=OLLAMA_BASE_URL,
                api_key=OLLAMA_API_KEY,
                timeout=300.0  # 5 минут на ответ (модель может думать долго)
            )
            logger.info(f"✅ Ollama подключен: {OLLAMA_BASE_URL}")
        except Exception as e:
            logger.warning(f"⚠️ Ollama недоступен: {e}. ИИ-анализ будет пропущен.")
        
        # 2. OCR для сканов (опционально)
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(use_angle_cls=True, lang='ru', use_gpu=False, show_log=False)
            logger.info("✅ PaddleOCR инициализирован")
        except Exception as e:
            logger.warning(f"⚠️ PaddleOCR недоступен: {e}. Сканы не будут распознаваться.")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Извлекает текст из PDF.
        Если страница — скан (мало текста), использует OCR.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("❌ PyMuPDF не установлен: pip install pymupdf")
            return ""
        
        doc = fitz.open(pdf_path)
        full_text = ""
        ocr_pages = 0
        
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            
            # Если текста мало (< 100 символов) — скорее всего это скан
            if len(text) < 100 and self.ocr is not None:
                logger.info(f"  📷 Страница {page_num+1}: распознаю через OCR")
                try:
                    pix = page.get_pixmap(dpi=200)  # 200 DPI для качества
                    img_bytes = pix.tobytes("png")
                    result = self.ocr.ocr(img_bytes, cls=True)
                    
                    text = ""
                    if result and result[0]:
                        for line in result[0]:
                            if line and len(line) >= 2:
                                text += line[1][0] + "\n"
                    ocr_pages += 1
                except Exception as e:
                    logger.warning(f"  ⚠️ OCR ошибка на стр. {page_num+1}: {e}")
            
            full_text += text + "\n\n"
        
        if ocr_pages > 0:
            logger.info(f"  📊 Распознано страниц через OCR: {ocr_pages}/{len(doc)}")
        
        return full_text
    
    def extract_tables_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """
        Извлекает таблицы из PDF через Camelot.
        Возвращает список таблиц в формате dict.
        """
        try:
            import camelot
        except ImportError:
            logger.warning("⚠️ Camelot не установлен: pip install camelot-py[cv]. Таблицы не извлечены.")
            return []
        
        tables_data = []
        try:
            tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice')
            for i, table in enumerate(tables):
                df = table.df
                tables_data.append({
                    "table_index": i,
                    "page": table.p[0],
                    "rows": df.to_dict('records'),
                    "columns": list(df.columns)
                })
            logger.info(f"  📊 Извлечено таблиц: {len(tables_data)}")
        except Exception as e:
            logger.warning(f"  ⚠️ Ошибка извлечения таблиц: {e}")
        
        return tables_data
    
    def _build_prompt(self, text: str, tables: List[Dict], client_name: str) -> str:
        """Формирует промпт для ИИ"""
        # Обрезаем текст если слишком длинный (контекст модели ~32K токенов)
        max_chars = 25000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... текст обрезан из-за длины ...]"
        
        tables_str = json.dumps(tables, ensure_ascii=False, indent=2) if tables else "Таблицы не найдены"
        
        return f"""Ты — эксперт по анализу технических документов в нефтегазовой отрасли (ТЗ, договоры на бурение, технологические регламенты).

Твоя задача: извлечь ВСЕ технологические лимиты, ограничения и требования из документа в строгом формате JSON.

ЗАКАЗЧИК: {client_name}

ТЕКСТ ДОКУМЕНТА:
{text}

ТАБЛИЦЫ ИЗ ДОКУМЕНТА:
{tables_str}

ИЗВЛЕКИ следующие параметры (ТОЛЬКО если они явно указаны в документе):
1. Лимиты по интенсивности искривления ствола (DLS) — обычно в °/10м или град/10м
2. Лимиты по содержанию песка в буровом растворе — в %
3. Буфер ЭЦП до давления ГРП/поглощения — в г/см³
4. Межповерочный интервал ВЗД — в часах
5. Ограничения по плотности раствора — в г/см³
6. Ограничения по осевой нагрузке (WOB) — в тоннах
7. Температурные ограничения — в °C

ФОРМАТ ОТВЕТА (строго JSON, без markdown):
{{
  "rules": [
    {{
      "rule_id": "уникальный_id_параметра",
      "category": "dls_limit | sand_limit | ecd_buffer | mpi_hours | mud_density | wob_limit | temperature_limit",
      "parameter": "max_dls | max_sand_content | min_ecd_buffer | vzd_mpi | max_mud_density | max_wob | max_temperature",
      "value": 3.0,
      "unit": "°/10м | % | г/см³ | часов | г/см³ | т | °C",
      "description": "Краткое описание требования из текста",
      "source_text": "Цитата из документа, откуда взято значение",
      "mandatory": true
    }}
  ],
  "document_info": {{
    "title": "Название документа если есть",
    "date": "Дата документа если есть",
    "client": "{client_name}"
  }}
}}

ПРАВИЛА:
- Возвращай ТОЛЬКО JSON, без пояснений и markdown-блоков
- Если параметр не найден — НЕ включай его в результат
- Значения должны быть ЧИСЛАМИ (float), не строками
- unit должен точно соответствовать единице из документа
- source_text — обязательное поле, цитата из документа
- Если в документе несколько значений для одного параметра — бери самое строгое (минимальное для лимитов)"""
    
    def _call_llm(self, prompt: str) -> str:
        """Вызов локальной LLM через Ollama"""
        if self.client is None:
            raise RuntimeError("Ollama клиент не инициализирован")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты — строгий аналитик технических документов. Отвечай только валидным JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """Парсит JSON из ответа ИИ с обработкой ошибок"""
        # 1. Пробуем прямой парсинг
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # 2. Ищем JSON между { и }
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        # 3. Пробуем очистить от markdown-блоков
        cleaned = re.sub(r'^```json\s*', '', response_text)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        logger.error("❌ Не удалось распарсить JSON из ответа ИИ")
        logger.debug(f"Ответ ИИ: {response_text[:500]}")
        return {"rules": [], "error": "JSON parse failed"}
    
    def _validate_rules(self, rules: List[Dict]) -> List[Dict]:
        """Валидация извлеченных правил"""
        valid_rules = []
        for rule in rules:
            # Обязательные поля
            required = ["rule_id", "category", "parameter", "value", "unit"]
            if not all(k in rule for k in required):
                logger.warning(f"  ⚠️ Правило без обязательных полей пропущено: {rule.get('rule_id', 'unknown')}")
                continue
            
            # Валидация категории
            if rule["category"] not in TARGET_CATEGORIES:
                logger.warning(f"  ⚠️ Неизвестная категория: {rule['category']}")
                continue
            
            # Валидация значения
            try:
                rule["value"] = float(rule["value"])
            except (ValueError, TypeError):
                logger.warning(f"  ⚠️ Некорректное значение: {rule['value']}")
                continue
            
            # Добавляем метаданные
            rule["mandatory"] = rule.get("mandatory", True)
            rule["effective_date"] = rule.get("effective_date", datetime.now().strftime("%Y-%m-%d"))
            rule["priority"] = 3  # Локальный уровень (из ТЗ)
            rule["client_hierarchy"] = rule.get("client_hierarchy", "Прочие")
            
            valid_rules.append(rule)
        
        return valid_rules
    
    def process_document(self, pdf_path: Path, client_name: str) -> Dict:
        """
        Полный цикл обработки одного PDF-документа.
        Возвращает структурированный JSON с правилами.
        """
        logger.info(f"📄 Обработка: {pdf_path.name} (Заказчик: {client_name})")
        
        # 1. Извлечение текста
        text = self.extract_text_from_pdf(pdf_path)
        if not text.strip():
            logger.error(f"  ❌ Текст не извлечен из {pdf_path.name}")
            return {"rules": [], "error": "Empty text"}
        
        logger.info(f"  📝 Извлечено символов: {len(text)}")
        
        # 2. Извлечение таблиц
        tables = self.extract_tables_from_pdf(pdf_path)
        
        # 3. ИИ-анализ
        if self.client is None:
            logger.error("  ❌ Ollama недоступен. Пропускаю ИИ-анализ.")
            return {"rules": [], "error": "Ollama unavailable"}
        
        prompt = self._build_prompt(text, tables, client_name)
        
        try:
            logger.info(f"  🤖 Вызов модели {self.model}...")
            response_text = self._call_llm(prompt)
            result = self._parse_json_response(response_text)
        except Exception as e:
            logger.error(f"  ❌ Ошибка вызова ИИ: {e}")
            return {"rules": [], "error": str(e)}
        
        # 4. Валидация
        rules = result.get("rules", [])
        valid_rules = self._validate_rules(rules)
        
        logger.info(f"  ✅ Извлечено правил: {len(valid_rules)} из {len(rules)}")
        
        # 5. Формирование итогового результата
        return {
            "rules": valid_rules,
            "metadata": {
                "source_file": pdf_path.name,
                "client": client_name,
                "processed_date": datetime.now().isoformat(),
                "model": self.model,
                "total_pages": len(text) // 3000,  # Грубая оценка
                "ocr_used": self.ocr is not None
            },
            "document_info": result.get("document_info", {})
        }
    
    def detect_client_from_filename(self, filename: str) -> str:
        """Пытается определить заказчика из имени файла"""
        name_lower = filename.lower()
        
        client_map = {
            "tatneft": "Татнефть",
            "татнефть": "Татнефть",
            "rosneft": "Роснефть",
            "роснефть": "Роснефть",
            "gazprom": "Газпром нефть",
            "газпром": "Газпром нефть",
            "lukoil": "ЛУКОЙЛ",
            "лукойл": "ЛУКОЙЛ",
            "novatek": "НОВАТЭК",
            "новатэк": "НОВАТЭК"
        }
        
        for key, client in client_map.items():
            if key in name_lower:
                return client
        
        return "Прочие"


# ============================================================================
# CLI ИНТЕРФЕЙС
# ============================================================================

def process_folder(input_dir: Path, output_file: Path, parser: LocalDocParser) -> Dict:
    """Обработать все PDF в папке"""
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.error(f"❌ PDF-файлы не найдены в {input_dir}")
        return {"total": 0, "success": 0, "errors": 0}
    
    logger.info(f" Найдено PDF: {len(pdf_files)}")
    
    all_rules = []
    all_metadata = []
    success_count = 0
    error_count = 0
    
    for pdf_file in pdf_files:
        # Определяем заказчика
        client_name = parser.detect_client_from_filename(pdf_file.stem)
        
        try:
            result = parser.process_document(pdf_file, client_name)
            
            if "error" in result:
                error_count += 1
                continue
            
            all_rules.extend(result["rules"])
            all_metadata.append(result["metadata"])
            success_count += 1
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка обработки {pdf_file.name}: {e}")
            error_count += 1
    
    # Формирование итогового JSON
    output_data = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "total_documents": len(pdf_files),
        "successful": success_count,
        "errors": error_count,
        "rules": all_rules,
        "metadata": all_metadata
    }
    
    # Сохранение
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 Сохранено в: {output_file}")
    logger.info(f"📊 Итого: {len(all_rules)} правил из {success_count} документов")
    
    return {"total": len(pdf_files), "success": success_count, "errors": error_count, "rules": len(all_rules)}


def main():
    """Точка входа CLI"""
    parser_cli = argparse.ArgumentParser(description="Локальный ИИ-парсер технических документов")
    parser_cli.add_argument("--file", type=str, help="Обработать один PDF-файл")
    parser_cli.add_argument("--folder", type=str, help="Папка с PDF (по умолчанию: data/input_docs)")
    parser_cli.add_argument("--output", type=str, help="Выходной файл (по умолчанию: data/kb_update.json)")
    parser_cli.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Модель Ollama (по умолчанию: {DEFAULT_MODEL})")
    parser_cli.add_argument("--client", type=str, help="Заказчик (если не определяется из имени файла)")
    
    args = parser_cli.parse_args()
    
    logger.info("=" * 60)
    logger.info("ЛОКАЛЬНЫЙ ИИ-ПАРСЕР ТЕХНИЧЕСКИХ ДОКУМЕНТОВ")
    logger.info("=" * 60)
    
    # Инициализация парсера
    parser = LocalDocParser(model=args.model)
    
    # Определяем пути
    project_root = Path(__file__).parent.parent
    input_dir = Path(args.folder) if args.folder else project_root / "data" / "input_docs"
    output_file = Path(args.output) if args.output else project_root / "data" / "kb_update.json"
    
    # Обработка одного файла
    if args.file:
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            logger.error(f"❌ Файл не найден: {pdf_path}")
            sys.exit(1)
        
        client_name = args.client or parser.detect_client_from_filename(pdf_path.stem)
        result = parser.process_document(pdf_path, client_name)
        
        # Сохранение
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Готово! Правил: {len(result.get('rules', []))}")
        logger.info(f"💾 Сохранено: {output_file}")
        return
    
    # Обработка папки
    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Создана папка: {input_dir}. Положите туда PDF и запустите снова.")
        sys.exit(0)
    
    stats = process_folder(input_dir, output_file, parser)
    
    logger.info("=" * 60)
    logger.info(f"РЕЗУЛЬТАТ: {stats['success']}/{stats['total']} документов, {stats['rules']} правил")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
