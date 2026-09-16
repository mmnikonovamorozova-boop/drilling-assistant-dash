"""
ЦЕНТРАЛЬНЫЙ МОДУЛЬ СИНХРОНИЗАЦИИ ДЛЯ ИНЖЕНЕРА В ОФИСЕ
Три кнопки:
1. Импорт данных с буровых
2. Объединить все базы
3. Экспорт центральной базы (для развоза по буровым)
"""
import pandas as pd
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import shutil


class OfficeSyncManager:
    """Менеджер синхронизации для центрального офиса"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Центральная база знаний (агрегированная)
        self.central_db = self.data_dir / "central_knowledge.db"
        
        # Папка для входящих файлов с буровых
        self.incoming_dir = self.data_dir / "incoming_from_burovaya"
        self.incoming_dir.mkdir(exist_ok=True)
        
        # Папка для исходящих обновлений (для развоза)
        self.outgoing_dir = self.data_dir / "outgoing_to_burovaya"
        self.outgoing_dir.mkdir(exist_ok=True)
        
        # Инициализация центральной БД
        self._init_central_database()
    
    def _init_central_database(self):
        """Создает центральную базу данных если её нет"""
        if not self.central_db.exists():
            conn = sqlite3.connect(self.central_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    burovaya_id TEXT,
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
                    import_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(burovaya_id, date, well, vendor)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    burovaya_id TEXT,
                    records_count INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
    
    def import_from_burovaya(self, json_file_path: str, burovaya_id: str = None) -> tuple[bool, str]:
        """
        КНОПКА 1: Импорт данных с буровой
        Загружает JSON-файл с флешки в центральную базу
        
        Args:
            json_file_path: Путь к файлу DDR_export_*.json
            burovaya_id: ID буровой (если не указан в файле)
        
        Returns:
            (success: bool, message: str)
        """
        try:
            if not Path(json_file_path).exists():
                return False, "Файл не найден"
            
            # Чтение JSON
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Если данные в формате списка записей
            if isinstance(data, list):
                df_new = pd.DataFrame(data)
            elif "daily_reports" in data:
                df_new = pd.DataFrame(data["daily_reports"])
            else:
                return False, "Неверный формат файла"
            
            if df_new.empty:
                return False, "Файл пуст"
            
            # Определение ID буровой
            if burovaya_id is None:
                # Пытаемся извлечь из метаданных
                burovaya_id = df_new.iloc[0].get('burovaya_id', 'unknown')
            
            # Добавляем колонку burovaya_id если нет
            if 'burovaya_id' not in df_new.columns:
                df_new['burovaya_id'] = burovaya_id
            
            # Запись в центральную БД
            conn = sqlite3.connect(self.central_db)
            
            # Используем UPSERT для избежания дубликатов
            for _, row in df_new.iterrows():
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_reports 
                        (burovaya_id, date, field, well, vendor, vzd_hours, sand_pct, temp_c, dls, rop, failure_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('burovaya_id', burovaya_id),
                        row.get('date'),
                        row.get('field'),
                        row.get('well'),
                        row.get('vendor'),
                        row.get('vzd_hours'),
                        row.get('sand_pct'),
                        row.get('temp_c'),
                        row.get('dls'),
                        row.get('rop'),
                        row.get('failure_type')
                    ))
                except Exception as e:
                    print(f"Ошибка записи строки: {e}")
                    continue
            
            # Логирование импорта
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_log (action, burovaya_id, records_count)
                VALUES (?, ?, ?)
            """, ('IMPORT', burovaya_id, len(df_new)))
            
            conn.commit()
            conn.close()
            
            # Перемещение файла в архив
            archive_path = self.incoming_dir / f"processed_{Path(json_file_path).name}"
            shutil.move(json_file_path, archive_path)
            
            message = f"✅ Импортировано {len(df_new)} записей с буровой {burovaya_id}"
            return True, message
            
        except Exception as e:
            return False, f"❌ Ошибка импорта: {str(e)}"
    
    def merge_all_bases(self) -> tuple[bool, str]:
        """
        КНОПКА 2: Объединить все базы
        Агрегирует данные, пересчитывает статистику, обновляет vendor_knowledge_base
        
        Returns:
            (success: bool, message: str)
        """
        try:
            conn = sqlite3.connect(self.central_db)
            
            # Получаем все данные
            df_all = pd.read_sql("SELECT * FROM daily_reports", conn)
            
            if df_all.empty:
                conn.close()
                return False, "Центральная база пуста. Сначала импортируйте данные с буровых."
            
            # Пересчет статистики по вендорам и регионам
            vendor_stats = df_all.groupby(['vendor', 'field']).agg({
                'vzd_hours': ['mean', 'std', 'count'],
                'sand_pct': 'mean',
                'dls': 'mean'
            }).round(2)
            
            vendor_stats.columns = ['avg_hours', 'std_hours', 'count', 'avg_sand', 'avg_dls']
            vendor_stats = vendor_stats.reset_index()
            
            # Анализ отказов
            if 'failure_type' in df_all.columns:
                failure_stats = df_all[df_all['failure_type'].notna()].groupby(
                    ['vendor', 'failure_type']
                ).size().reset_index(name='count')
            else:
                failure_stats = pd.DataFrame()
            
            # Генерация обновленного vendor_knowledge_base.py
            self._generate_updated_knowledge_base(vendor_stats, failure_stats)
            
            # Логирование
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_log (action, burovaya_id, records_count)
                VALUES (?, ?, ?)
            """, ('MERGE', 'ALL', len(df_all)))
            
            conn.commit()
            conn.close()
            
            unique_burovayas = df_all['burovaya_id'].nunique()
            message = f"✅ База объединена! Всего записей: {len(df_all)}, буровых: {unique_burovayas}"
            return True, message
            
        except Exception as e:
            return False, f"❌ Ошибка объединения: {str(e)}"
    
    def export_central_update(self) -> tuple[bool, str, str]:
        """
        КНОПКА 3: Экспорт центральной базы
        Создает файл central_update.json для развоза по буровым
        
        Returns:
            (success: bool, message: str, file_path: str)
        """
        try:
            conn = sqlite3.connect(self.central_db)
            
            # Экспорт всех данных
            df_all = pd.read_sql("SELECT * FROM daily_reports", conn)
            conn.close()
            
            if df_all.empty:
                return False, "База пуста", ""
            
            # Создание JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"central_update_{timestamp}.json"
            filepath = self.outgoing_dir / filename
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_records": len(df_all),
                "burovayas_count": df_all['burovaya_id'].nunique(),
                "daily_reports": df_all.to_dict('records')
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            message = f"✅ Файл для развоза создан: {filename}"
            return True, message, str(filepath)
            
        except Exception as e:
            return False, f"❌ Ошибка экспорта: {str(e)}", ""
    
    def _generate_updated_knowledge_base(self, vendor_stats: pd.DataFrame, failure_stats: pd.DataFrame):
        """
        Генерирует обновленный файл vendor_knowledge_base.py
        на основе реальных данных
        """
        # Здесь можно добавить логику генерации Python файла
        # Пока просто сохраняем статистику в JSON
        stats_file = self.data_dir / "vendor_statistics.json"
        
        stats_data = {
            "last_updated": datetime.now().isoformat(),
            "vendor_stats": vendor_stats.to_dict('records'),
            "failure_stats": failure_stats.to_dict('records') if not failure_stats.empty else []
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
    
    def get_sync_statistics(self) -> dict:
        """Получает статистику синхронизации"""
        try:
            conn = sqlite3.connect(self.central_db)
            
            total_records = pd.read_sql("SELECT COUNT(*) as count FROM daily_reports", conn)["count"].iloc[0]
            unique_burovayas = pd.read_sql("SELECT COUNT(DISTINCT burovaya_id) as count FROM daily_reports", conn)["count"].iloc[0]
            sync_log = pd.read_sql("SELECT * FROM sync_log ORDER BY timestamp DESC LIMIT 10", conn)
            
            conn.close()
            
            return {
                "total_records": total_records,
                "unique_burovayas": unique_burovayas,
                "recent_syncs": sync_log.to_dict('records')
            }
        except:
            return {"total_records": 0, "unique_burovayas": 0, "recent_syncs": []}
