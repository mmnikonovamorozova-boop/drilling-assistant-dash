"""
МЕНЕДЖЕР СИНХРОНИЗАЦИИ ДАННЫХ
Три простые кнопки для буровиков:
1. Выгрузить DDR
2. Экспорт данных  
3. Обновить базу знаний
"""
import pandas as pd
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import shutil


class SyncManager:
    """Управление синхронизацией данных между буровой и офисом"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.local_db = self.data_dir / "local_knowledge.db"
        self.ddr_folder = self.data_dir / "ddr_exports"
        self.ddr_folder.mkdir(exist_ok=True)
    
    def export_ddr_data(self) -> tuple[bool, str, str]:
        """
        КНОПКА 1: Выгрузить DDR
        Экспортирует данные из дейликов в JSON для синхронизации
        
        Returns:
            (success: bool, message: str, file_path: str)
        """
        try:
            # Чтение локальной базы
            if not self.local_db.exists():
                return False, "Локальная база данных не найдена", ""
            
            conn = sqlite3.connect(self.local_db)
            
            # Экспорт таблицы daily_reports
            df = pd.read_sql("SELECT * FROM daily_reports", conn)
            conn.close()
            
            if df.empty:
                return False, "Нет данных для экспорта. Загрузите дейлики.", ""
            
            # Сохранение в JSON с временной меткой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DDR_export_{timestamp}.json"
            filepath = self.ddr_folder / filename
            
            df.to_json(filepath, orient='records', date_format='iso', force_ascii=False)
            
            record_count = len(df)
            message = f"✅ Успешно выгружено {record_count} записей из дейликов"
            
            return True, message, str(filepath)
            
        except Exception as e:
            return False, f"❌ Ошибка экспорта DDR: {str(e)}", ""
    
    def export_full_database(self) -> tuple[bool, str, str]:
        """
        КНОПКА 2: Экспорт данных
        Полный экспорт локальной базы знаний (SQLite + метаданные)
        
        Returns:
            (success: bool, message: str, file_path: str)
        """
        try:
            if not self.local_db.exists():
                return False, "Локальная база данных не найдена", ""
            
            # Создание резервной копии SQLite
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"KnowledgeDB_backup_{timestamp}.db"
            backup_path = self.data_dir / backup_filename
            
            shutil.copy2(self.local_db, backup_path)
            
            # Экспорт метаданных (статистика)
            conn = sqlite3.connect(self.local_db)
            stats = {
                "total_records": pd.read_sql("SELECT COUNT(*) as count FROM daily_reports", conn)["count"].iloc[0],
                "export_timestamp": datetime.now().isoformat(),
                "burovaya_id": self._get_burovaya_id()
            }
            conn.close()
            
            # Сохранение метаданных
            stats_file = self.data_dir / f"Metadata_{timestamp}.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            message = f"✅ База знаний экспортирована: {backup_filename}"
            return True, message, str(backup_path)
            
        except Exception as e:
            return False, f"❌ Ошибка экспорта базы: {str(e)}", ""
    
    def import_central_knowledge(self, json_file_path: str) -> tuple[bool, str]:
        """
        КНОПКА 3: Обновить базу знаний
        Импорт обновлений из центральной базы (полученных через флешку/сеть)
        
        Args:
            json_file_path: Путь к файлу central_update.json
        
        Returns:
            (success: bool, message: str)
        """
        try:
            if not Path(json_file_path).exists():
                return False, "Файл обновления не найден"
            
            # Чтение обновлений
            with open(json_file_path, 'r', encoding='utf-8') as f:
                update_data = json.load(f)
            
            # Проверка структуры
            if "daily_reports" not in update_data:
                return False, "Неверный формат файла обновления"
            
            df_new = pd.DataFrame(update_data["daily_reports"])
            
            if df_new.empty:
                return False, "Файл обновления пуст"
            
            # Инициализация локальной базы если нет
            if not self.local_db.exists():
                self._init_local_database()
            
            # Слияние данных
            conn = sqlite3.connect(self.local_db)
            
            # Чтение существующих данных
            df_existing = pd.read_sql("SELECT * FROM daily_reports", conn)
            
            # Объединение без дубликатов
            df_merged = pd.concat([df_existing, df_new], ignore_index=True)
            df_merged = df_merged.drop_duplicates(subset=['date', 'well', 'vendor'], keep='last')
            
            # Запись обратно
            df_merged.to_sql('daily_reports', conn, if_exists='replace', index=False)
            
            record_count = len(df_merged)
            new_records = len(df_new)
            
            conn.close()
            
            message = f"✅ База знаний обновлена! Всего записей: {record_count}, новых: {new_records}"
            return True, message
            
        except Exception as e:
            return False, f"❌ Ошибка импорта: {str(e)}"
    
    def _init_local_database(self):
        """Инициализация локальной базы данных"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                field TEXT,
                well TEXT,
                vendor TEXT,
                vzd_hours REAL,
                sand_pct REAL,
                temp_c REAL,
                dls REAL,
                rop REAL,
                failure_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _get_burovaya_id(self) -> str:
        """Получение ID буровой из конфига"""
        config_path = Path("config/burovaya_id.txt")
        if config_path.exists():
            return config_path.read_text().strip()
        return "unknown"
    
    def prepare_usb_sync_package(self) -> tuple[bool, str, str]:
        """
        Подготовка пакета для синхронизации через флешку
        Создает ZIP-архив со всеми экспортами
        """
        import zipfile
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"SyncPackage_{timestamp}.zip"
            zip_path = self.data_dir / zip_filename
            
            # Создание ZIP-архива
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Добавление DDR экспортов
                for ddr_file in self.ddr_folder.glob("*.json"):
                    zipf.write(ddr_file, f"ddr/{ddr_file.name}")
                
                # Добавление последней базы данных
                if self.local_db.exists():
                    zipf.write(self.local_db, "database/local_knowledge.db")
                
                # Добавление метаданных
                burovaya_id = self._get_burovaya_id()
                metadata = {
                    "burovaya_id": burovaya_id,
                    "export_timestamp": datetime.now().isoformat(),
                    "version": "1.0"
                }
                metadata_file = self.data_dir / "sync_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                zipf.write(metadata_file, "metadata.json")
            
            message = f"✅ Пакет синхронизации создан: {zip_filename}"
            return True, message, str(zip_path)
            
        except Exception as e:
            return False, f"❌ Ошибка создания пакета: {str(e)}", ""
