import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class SyncManager:
    def __init__(self, db_path: str, config_manager=None):
        from .config_manager import ConfigManager
        
        self.db_path = db_path
        self.config = config_manager or ConfigManager()
        self.sync_enabled = self.config.get('sync.enabled', True)
        self.sync_interval = self.config.get('sync.interval_minutes', 30)
        self.auto_sync = self.config.get('sync.auto', True)
        
        self._init_sync_tables()
    
    def _init_sync_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    record_id INTEGER,
                    data TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    server_id INTEGER,
                    checksum TEXT,
                    INDEX (status),
                    INDEX (timestamp)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    record_id INTEGER,
                    status TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    duration_ms INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY,
                    last_sync_time DATETIME,
                    last_sync_status TEXT,
                    last_sync_error TEXT,
                    pending_count INTEGER DEFAULT 0,
                    last_successful_sync DATETIME
                )
            """)
            
            conn.execute("""
                INSERT OR IGNORE INTO sync_status (id, pending_count)
                VALUES (1, 0)
            """)
            
            conn.commit()
    
    def is_enabled(self) -> bool:
        return self.sync_enabled
    
    def enable(self):
        self.sync_enabled = True
        self.config.set('sync.enabled', True)
    
    def disable(self):
        self.sync_enabled = False
        self.config.set('sync.enabled', False)
    
    def queue_operation(self, operation_type: str, table_name: str, 
                      record_id: Optional[int], data: Dict) -> int:
        if not self.is_enabled():
            return -1
        
        data_json = json.dumps(data, ensure_ascii=False)
        checksum = self._calculate_checksum(data_json)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_queue 
                (operation_type, table_name, record_id, data, checksum, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            """, (operation_type, table_name, record_id, data_json, checksum))
            
            sync_id = cursor.lastrowid
            conn.execute("""
                UPDATE sync_status 
                SET pending_count = (SELECT COUNT(*) FROM sync_queue WHERE status = 'pending')
                WHERE id = 1
            """)
            conn.commit()
            
            return sync_id
    
    def queue_insert(self, table_name: str, data: Dict) -> int:
        return self.queue_operation('insert', table_name, None, data)
    
    def queue_update(self, table_name: str, record_id: int, data: Dict) -> int:
        return self.queue_operation('update', table_name, record_id, data)
    
    def queue_delete(self, table_name: str, record_id: int, data: Dict) -> int:
        return self.queue_operation('delete', table_name, record_id, data)
    
    def get_pending_operations(self, limit: int = 100) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_queue 
                WHERE status = 'pending' 
                ORDER BY timestamp ASC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'
            """)
            return cursor.fetchone()[0]
    
    def sync_all(self) -> Tuple[bool, Dict]:
        if not self.is_enabled():
            return False, {'error': 'Sync is disabled'}
        
        operations = self.get_pending_operations()
        
        if not operations:
            return True, {'message': 'No pending operations', 'synced': 0}
        
        results = {
            'total': len(operations),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for operation in operations:
            success = self._sync_operation(operation)
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'id': operation['id'],
                    'error': 'Failed to sync'
                })
        
        self._update_sync_status(results['success'] > 0)
        
        return results['failed'] == 0, results
    
    def _sync_operation(self, operation: Dict) -> bool:
        try:
            import requests
            
            api_url = self.config.get('sync.api_url', 'http://localhost:5000/api/sync')
            api_key = self.config.get('sync.api_key')
            
            headers = {'Content-Type': 'application/json'}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            start_time = datetime.now()
            
            data = {
                'operation_type': operation['operation_type'],
                'table_name': operation['table_name'],
                'record_id': operation['record_id'],
                'data': json.loads(operation['data']),
                'checksum': operation['checksum']
            }
            
            response = requests.post(
                api_url,
                json=data,
                headers=headers,
                timeout=30
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response.status_code == 200:
                result = response.json()
                
                self._mark_operation_success(
                    operation['id'],
                    result.get('server_id'),
                    duration_ms
                )
                
                self._log_sync_operation(
                    operation['operation_type'],
                    operation['table_name'],
                    operation['record_id'],
                    'success',
                    None,
                    duration_ms
                )
                
                return True
            else:
                self._mark_operation_failed(
                    operation['id'],
                    response.text
                )
                
                self._log_sync_operation(
                    operation['operation_type'],
                    operation['table_name'],
                    operation['record_id'],
                    'failed',
                    response.text,
                    duration_ms
                )
                
                return False
                
        except Exception as e:
            self._mark_operation_failed(
                operation['id'],
                str(e)
            )
            
            self._log_sync_operation(
                operation['operation_type'],
                operation['table_name'],
                operation['record_id'],
                'failed',
                str(e),
                0
            )
            
            return False
    
    def _mark_operation_success(self, operation_id: int, server_id: Optional[int], duration_ms: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sync_queue 
                SET status = 'synced', server_id = ?, retry_count = retry_count + 1
                WHERE id = ?
            """, (server_id, operation_id))
            
            conn.execute("""
                UPDATE sync_status 
                SET last_successful_sync = CURRENT_TIMESTAMP,
                    pending_count = (SELECT COUNT(*) FROM sync_queue WHERE status = 'pending')
                WHERE id = 1
            """)
            
            conn.commit()
    
    def _mark_operation_failed(self, operation_id: int, error_message: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sync_queue 
                SET status = 'failed', retry_count = retry_count + 1
                WHERE id = ?
            """, (operation_id,))
            
            conn.commit()
    
    def _log_sync_operation(self, operation_type: str, table_name: str, 
                          record_id: Optional[int], status: str, 
                          error_message: Optional[str], duration_ms: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sync_log 
                (operation_type, table_name, record_id, status, error_message, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (operation_type, table_name, record_id, status, error_message, duration_ms))
            
            conn.commit()
    
    def _update_sync_status(self, success: bool):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if success:
                cursor.execute("""
                    UPDATE sync_status 
                    SET last_sync_time = CURRENT_TIMESTAMP,
                        last_sync_status = 'success',
                        pending_count = (SELECT COUNT(*) FROM sync_queue WHERE status = 'pending')
                    WHERE id = 1
                """)
            else:
                cursor.execute("""
                    UPDATE sync_status 
                    SET last_sync_time = CURRENT_TIMESTAMP,
                        last_sync_status = 'failed'
                    WHERE id = 1
                """)
            
            conn.commit()
    
    def get_sync_status(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM sync_status WHERE id = 1")
            status_row = dict(cursor.fetchone())
            
            cursor.execute("""
                SELECT COUNT(*) as total_pending
                FROM sync_queue WHERE status = 'pending'
            """)
            pending_count = cursor.fetchone()['total_pending']
            
            cursor.execute("""
                SELECT COUNT(*) as failed_count
                FROM sync_queue WHERE status = 'failed'
            """)
            failed_count = cursor.fetchone()['failed_count']
            
            return {
                'last_sync_time': status_row.get('last_sync_time'),
                'last_sync_status': status_row.get('last_sync_status'),
                'last_sync_error': status_row.get('last_sync_error'),
                'last_successful_sync': status_row.get('last_successful_sync'),
                'pending_count': pending_count,
                'failed_count': failed_count,
                'enabled': self.is_enabled(),
                'auto_sync': self.auto_sync
            }
    
    def get_sync_log(self, limit: int = 100) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_log 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def retry_failed_operations(self) -> Tuple[bool, Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sync_queue 
                SET status = 'pending', retry_count = 0
                WHERE status = 'failed'
            """)
            conn.commit()
        
        return self.sync_all()
    
    def clear_failed_operations(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_queue WHERE status = 'failed'")
            deleted_count = cursor.rowcount
            conn.commit()
            
            return deleted_count
    
    def clear_sync_log(self, older_than_days: int = 30) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sync_log 
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (older_than_days,))
            deleted_count = cursor.rowcount
            conn.commit()
            
            return deleted_count
    
    def _calculate_checksum(self, data: str) -> str:
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    def get_conflicts(self) -> List[Dict]:
        conflicts = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name, record_id, COUNT(*) as conflict_count
                FROM sync_queue
                WHERE status IN ('pending', 'synced')
                GROUP BY table_name, record_id
                HAVING conflict_count > 1
            """)
            
            for row in cursor.fetchall():
                conflicts.append({
                    'table_name': row['table_name'],
                    'record_id': row['record_id'],
                    'conflict_count': row['conflict_count']
                })
        
        return conflicts
    
    def resolve_conflict(self, table_name: str, record_id: int, 
                        resolution: str) -> bool:
        if resolution not in ['keep_latest', 'keep_oldest', 'keep_server']:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if resolution == 'keep_latest':
                cursor.execute("""
                    DELETE FROM sync_queue
                    WHERE table_name = ? AND record_id = ?
                    AND id NOT IN (
                        SELECT id FROM sync_queue
                        WHERE table_name = ? AND record_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 1
                    )
                """, (table_name, record_id, table_name, record_id))
            
            elif resolution == 'keep_oldest':
                cursor.execute("""
                    DELETE FROM sync_queue
                    WHERE table_name = ? AND record_id = ?
                    AND id NOT IN (
                        SELECT id FROM sync_queue
                        WHERE table_name = ? AND record_id = ?
                        ORDER BY timestamp ASC
                        LIMIT 1
                    )
                """, (table_name, record_id, table_name, record_id))
            
            elif resolution == 'keep_server':
                cursor.execute("""
                    DELETE FROM sync_queue
                    WHERE table_name = ? AND record_id = ?
                    AND server_id IS NULL
                """, (table_name, record_id))
            
            conn.commit()
            return True
