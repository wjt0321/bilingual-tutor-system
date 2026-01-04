"""
Operations Manager
运维管理器 - 提供系统诊断、日志查看、缓存管理等功能
"""

import os
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """系统诊断"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            系统信息字典
        """
        import platform
        import psutil
        
        return {
            'hostname': platform.node(),
            'os': platform.system(),
            'os_version': platform.version(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'total_memory': psutil.virtual_memory().total,
            'disk_usage': {
                mount.mountpoint: {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                }
                for mount, disk in zip(psutil.disk_partitions(), 
                                     [psutil.disk_usage(mount.mountpoint) for mount in psutil.disk_partitions()])
            },
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
    
    @staticmethod
    def get_process_info(pid: Optional[int] = None) -> Dict[str, Any]:
        """
        获取进程信息
        
        Args:
            pid: 进程ID,为None则返回当前进程
        
        Returns:
            进程信息字典
        """
        import psutil
        
        if pid is None:
            pid = os.getpid()
        
        try:
            process = psutil.Process(pid)
            
            return {
                'pid': process.pid,
                'name': process.name(),
                'status': process.status(),
                'cpu_percent': process.cpu_percent(interval=1),
                'memory_info': {
                    'rss': process.memory_info().rss,
                    'vms': process.memory_info().vms
                },
                'num_threads': process.num_threads(),
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                'connections': len(process.connections()),
                'open_files': len(process.open_files())
            }
        except psutil.NoSuchProcess:
            return {'error': '进程不存在'}
    
    @staticmethod
    def check_dependencies() -> Dict[str, Any]:
        """
        检查依赖项
        
        Returns:
            依赖项状态
        """
        dependencies = {
            'flask': False,
            'sqlalchemy': False,
            'psutil': False,
            'requests': False,
            'pytest': False
        }
        
        for dep in dependencies:
            try:
                __import__(dep)
                dependencies[dep] = True
            except ImportError:
                pass
        
        return dependencies


class LogManager:
    """日志管理器"""
    
    def __init__(self, log_dir: str = 'logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
    
    def get_log_files(self) -> List[Dict[str, Any]]:
        """
        获取所有日志文件
        
        Returns:
            日志文件列表
        """
        log_files = []
        
        for log_file in self.log_dir.glob('*.log'):
            stat = log_file.stat()
            
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return sorted(log_files, key=lambda x: x['modified'], reverse=True)
    
    def read_log_file(self, filename: str, lines: int = 100) -> Dict[str, Any]:
        """
        读取日志文件
        
        Args:
            filename: 文件名
            lines: 读取行数
        
        Returns:
            日志内容和元数据
        """
        log_path = self.log_dir / filename
        
        if not log_path.exists():
            return {'error': '文件不存在'}
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # 获取最后N行
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            return {
                'filename': filename,
                'path': str(log_path),
                'total_lines': len(all_lines),
                'lines': recent_lines,
                'last_modified': datetime.fromtimestamp(log_path.stat().st_mtime).isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def search_logs(self, query: str, filename: Optional[str] = None,
                   max_results: int = 100) -> List[Dict[str, Any]]:
        """
        搜索日志
        
        Args:
            query: 搜索关键词
            filename: 文件名筛选,为None则搜索所有文件
            max_results: 最大结果数
        
        Returns:
            匹配的日志行
        """
        results = []
        
        files_to_search = [self.log_dir / filename] if filename else self.log_dir.glob('*.log')
        
        for log_file in files_to_search:
            if not log_file.exists():
                continue
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if query.lower() in line.lower():
                            results.append({
                                'filename': log_file.name,
                                'line_number': line_num,
                                'content': line.strip()
                            })
                            
                            if len(results) >= max_results:
                                return results
            except Exception as e:
                logger.error(f"搜索日志文件 {log_file} 失败: {e}")
        
        return results
    
    def delete_old_logs(self, days: int = 30) -> int:
        """
        删除旧日志
        
        Args:
            days: 保留天数
        
        Returns:
            删除的文件数量
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for log_file in self.log_dir.glob('*.log'):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if file_time < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"删除旧日志: {log_file}")
                except Exception as e:
                    logger.error(f"删除日志文件 {log_file} 失败: {e}")
        
        return deleted_count


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = 'cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        cache_files = list(self.cache_dir.glob('**/*'))
        total_size = sum(f.stat().st_size for f in cache_files if f.is_file())
        
        return {
            'cache_dir': str(self.cache_dir),
            'total_files': len([f for f in cache_files if f.is_file()]),
            'total_size': total_size,
            'total_size_human': self._format_size(total_size)
        }
    
    def clear_cache(self, pattern: str = '*') -> int:
        """
        清除缓存
        
        Args:
            pattern: 文件匹配模式
        
        Returns:
            清除的文件数量
        """
        cleared_count = 0
        
        for cache_file in self.cache_dir.glob(pattern):
            if cache_file.is_file():
                try:
                    cache_file.unlink()
                    cleared_count += 1
                    logger.info(f"清除缓存文件: {cache_file}")
                except Exception as e:
                    logger.error(f"清除缓存文件 {cache_file} 失败: {e}")
        
        return cleared_count
    
    def get_cache_files(self) -> List[Dict[str, Any]]:
        """
        获取缓存文件列表
        
        Returns:
            缓存文件列表
        """
        cache_files = []
        
        for cache_file in self.cache_dir.glob('**/*'):
            if not cache_file.is_file():
                continue
            
            stat = cache_file.stat()
            
            cache_files.append({
                'name': cache_file.name,
                'path': str(cache_file),
                'size': stat.st_size,
                'size_human': self._format_size(stat.st_size),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return sorted(cache_files, key=lambda x: x['modified'], reverse=True)
    
    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class BackupManager:
    """备份管理器"""
    
    def __init__(self, backup_dir: str = 'backups'):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, source_dir: str, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """
        创建备份
        
        Args:
            source_dir: 源目录
            backup_name: 备份名称,为None则自动生成
        
        Returns:
            备份结果
        """
        source_path = Path(source_dir)
        
        if not source_path.exists():
            return {'success': False, 'message': '源目录不存在'}
        
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / backup_name
        
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            shutil.copytree(source_path, backup_path)
            
            logger.info(f"创建备份: {backup_path}")
            
            return {
                'success': True,
                'message': '备份创建成功',
                'backup_path': str(backup_path),
                'backup_name': backup_name,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        列出所有备份
        
        Returns:
            备份列表
        """
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if not backup_dir.is_dir():
                continue
            
            stat = backup_dir.stat()
            
            backups.append({
                'name': backup_dir.name,
                'path': str(backup_dir),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'size': self._get_dir_size(backup_dir)
            })
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def restore_backup(self, backup_name: str, target_dir: str) -> Dict[str, Any]:
        """
        恢复备份
        
        Args:
            backup_name: 备份名称
            target_dir: 目标目录
        
        Returns:
            恢复结果
        """
        backup_path = self.backup_dir / backup_name
        target_path = Path(target_dir)
        
        if not backup_path.exists():
            return {'success': False, 'message': '备份不存在'}
        
        try:
            if target_path.exists():
                shutil.rmtree(target_path)
            
            shutil.copytree(backup_path, target_path)
            
            logger.info(f"恢复备份: {backup_path} -> {target_path}")
            
            return {
                'success': True,
                'message': '备份恢复成功',
                'backup_path': str(backup_path),
                'target_path': str(target_path)
            }
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def delete_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        删除备份
        
        Args:
            backup_name: 备份名称
        
        Returns:
            删除结果
        """
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {'success': False, 'message': '备份不存在'}
        
        try:
            shutil.rmtree(backup_path)
            logger.info(f"删除备份: {backup_path}")
            
            return {'success': True, 'message': '备份删除成功'}
        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _get_dir_size(dir_path: Path) -> int:
        """计算目录大小"""
        total_size = 0
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        
        return total_size


class OperationsManager:
    """运维管理器 - 统一运维功能接口"""
    
    def __init__(self):
        self.diagnostics = SystemDiagnostics()
        self.log_manager = LogManager()
        self.cache_manager = CacheManager()
        self.backup_manager = BackupManager()
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        获取系统概览
        
        Returns:
            系统概览信息
        """
        return {
            'system_info': self.diagnostics.get_system_info(),
            'process_info': self.diagnostics.get_process_info(),
            'dependencies': self.diagnostics.check_dependencies(),
            'cache_info': self.cache_manager.get_cache_info(),
            'log_files': self.log_manager.get_log_files()[:10],  # 最近的10个日志文件
            'backups': self.backup_manager.list_backups()[:5]  # 最近的5个备份
        }
    
    def run_diagnostic_check(self) -> Dict[str, Any]:
        """
        运行诊断检查
        
        Returns:
            诊断结果
        """
        checks = []
        
        # 检查依赖
        deps = self.diagnostics.check_dependencies()
        missing_deps = [dep for dep, installed in deps.items() if not installed]
        
        checks.append({
            'name': '依赖检查',
            'status': 'pass' if not missing_deps else 'fail',
            'message': f'所有依赖已安装' if not missing_deps else f'缺失依赖: {", ".join(missing_deps)}'
        })
        
        # 检查磁盘空间
        disk_usage = psutil.disk_usage('/')
        disk_status = 'pass' if disk_usage.percent < 90 else 'fail'
        
        checks.append({
            'name': '磁盘空间',
            'status': disk_status,
            'message': f'磁盘使用率: {disk_usage.percent:.1f}%'
        })
        
        # 检查内存
        mem = psutil.virtual_memory()
        mem_status = 'pass' if mem.percent < 90 else 'fail'
        
        checks.append({
            'name': '内存使用',
            'status': mem_status,
            'message': f'内存使用率: {mem.percent:.1f}%'
        })
        
        # 检查日志目录
        log_files = self.log_manager.get_log_files()
        checks.append({
            'name': '日志文件',
            'status': 'pass',
            'message': f'找到 {len(log_files)} 个日志文件'
        })
        
        # 检查缓存目录
        cache_info = self.cache_manager.get_cache_info()
        checks.append({
            'name': '缓存目录',
            'status': 'pass',
            'message': f'缓存大小: {cache_info["total_size_human"]}'
        })
        
        return {
            'checks': checks,
            'overall_status': 'pass' if all(c['status'] == 'pass' for c in checks) else 'fail',
            'timestamp': datetime.now().isoformat()
        }


import psutil


operations_manager = OperationsManager()
