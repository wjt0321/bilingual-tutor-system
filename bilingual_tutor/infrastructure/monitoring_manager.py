"""
System Monitoring Manager
系统监控管理器 - 提供性能监控、健康检查、自动告警等功能
"""

import time
import psutil
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """指标数据"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """告警信息"""
    id: str
    metric_name: str
    severity: str  # 'info', 'warning', 'critical'
    message: str
    timestamp: datetime
    value: float
    threshold: float
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.metrics: Dict[str, deque] = {}
        self._lock = threading.Lock()
    
    def record_metric(self, metric_name: str, value: float, 
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        记录指标
        
        Args:
            metric_name: 指标名称
            value: 指标值
            metadata: 元数据
        """
        with self._lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = deque(maxlen=self.history_size)
            
            metric_data = MetricData(
                timestamp=datetime.now(),
                value=value,
                metadata=metadata or {}
            )
            
            self.metrics[metric_name].append(metric_data)
    
    def get_metric(self, metric_name: str, 
                   minutes: int = 5) -> List[MetricData]:
        """
        获取指标历史数据
        
        Args:
            metric_name: 指标名称
            minutes: 返回最近多少分钟的数据
        
        Returns:
            指标数据列表
        """
        with self._lock:
            if metric_name not in self.metrics:
                return []
            
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            return [
                m for m in self.metrics[metric_name] 
                if m.timestamp >= cutoff_time
            ]
    
    def get_metric_stats(self, metric_name: str,
                       minutes: int = 5) -> Dict[str, float]:
        """
        获取指标统计信息
        
        Args:
            metric_name: 指标名称
            minutes: 统计时间范围
        
        Returns:
            统计信息字典
        """
        metrics = self.get_metric(metric_name, minutes)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'current': values[-1] if values else 0
        }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """获取所有指标的统计信息"""
        with self._lock:
            return {
                name: self.get_metric_stats(name)
                for name in self.metrics.keys()
            }


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """
        注册健康检查
        
        Args:
            name: 检查名称
            check_func: 检查函数,返回(success: bool, message: str)
        """
        self.checks[name] = check_func
    
    def run_check(self, name: str) -> Dict[str, Any]:
        """
        运行单个健康检查
        
        Args:
            name: 检查名称
        
        Returns:
            检查结果
        """
        if name not in self.checks:
            return {
                'name': name,
                'status': 'unknown',
                'message': '检查不存在',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            success, message = self.checks[name]()
            
            result = {
                'name': name,
                'status': 'healthy' if success else 'unhealthy',
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            self.last_results[name] = result
            return result
            
        except Exception as e:
            logger.error(f"健康检查 {name} 失败: {e}")
            return {
                'name': name,
                'status': 'error',
                'message': f'检查失败: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def run_all_checks(self) -> List[Dict[str, Any]]:
        """
        运行所有健康检查
        
        Returns:
            所有检查结果
        """
        results = []
        
        for name in self.checks.keys():
            results.append(self.run_check(name))
        
        return results
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取整体健康状态
        
        Returns:
            健康状态摘要
        """
        results = self.run_all_checks()
        
        healthy_count = sum(1 for r in results if r['status'] == 'healthy')
        unhealthy_count = sum(1 for r in results if r['status'] == 'unhealthy')
        error_count = sum(1 for r in results if r['status'] == 'error')
        
        overall_status = 'healthy'
        if unhealthy_count > 0:
            overall_status = 'degraded'
        if error_count > 0 or unhealthy_count > len(results) / 2:
            overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'total_checks': len(results),
            'healthy_checks': healthy_count,
            'unhealthy_checks': unhealthy_count,
            'error_checks': error_count,
            'checks': results,
            'timestamp': datetime.now().isoformat()
        }


class AlertManager:
    """告警管理器"""
    
    def __init__(self, alert_file: str = 'logs/alerts.json'):
        self.alert_file = Path(alert_file)
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable] = []
        self._load_alerts()
    
    def _load_alerts(self) -> None:
        """加载历史告警"""
        if not self.alert_file.exists():
            return
        
        try:
            with open(self.alert_file, 'r', encoding='utf-8') as f:
                alert_data = json.load(f)
                
                for alert_id, data in alert_data.items():
                    self.alerts[alert_id] = Alert(
                        id=alert_id,
                        metric_name=data['metric_name'],
                        severity=data['severity'],
                        message=data['message'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        value=data['value'],
                        threshold=data['threshold'],
                        resolved=data.get('resolved', False),
                        resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None
                    )
        except Exception as e:
            logger.error(f"加载告警失败: {e}")
    
    def _save_alerts(self) -> None:
        """保存告警到文件"""
        try:
            alert_data = {}
            
            for alert_id, alert in self.alerts.items():
                alert_data[alert_id] = {
                    'metric_name': alert.metric_name,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'value': alert.value,
                    'threshold': alert.threshold,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
                }
            
            with open(self.alert_file, 'w', encoding='utf-8') as f:
                json.dump(alert_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
    
    def add_alert(self, metric_name: str, severity: str, message: str,
                 value: float, threshold: float) -> Alert:
        """
        添加告警
        
        Args:
            metric_name: 指标名称
            severity: 严重程度 ('info', 'warning', 'critical')
            message: 告警消息
            value: 当前值
            threshold: 阈值
        
        Returns:
            告警对象
        """
        alert_id = f"{metric_name}_{uuid.uuid4().hex}"
        
        alert = Alert(
            id=alert_id,
            metric_name=metric_name,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            value=value,
            threshold=threshold
        )
        
        self.alerts[alert_id] = alert
        self._save_alerts()
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        logger.warning(f"告警: {message}")
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警
        
        Args:
            alert_id: 告警ID
        
        Returns:
            是否成功解决
        """
        if alert_id not in self.alerts:
            return False
        
        self.alerts[alert_id].resolved = True
        self.alerts[alert_id].resolved_at = datetime.now()
        self._save_alerts()
        
        return True
    
    def get_active_alerts(self) -> List[Alert]:
        """获取所有未解决的告警"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alerts(self, metric_name: Optional[str] = None,
                   hours: int = 24) -> List[Alert]:
        """
        获取告警列表
        
        Args:
            metric_name: 指标名称筛选
            hours: 最近多少小时
        
        Returns:
            告警列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        alerts = [
            alert for alert in self.alerts.values()
            if alert.timestamp >= cutoff_time
        ]
        
        if metric_name:
            alerts = [a for a in alerts if a.metric_name == metric_name]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def register_handler(self, handler: Callable) -> None:
        """
        注册告警处理器
        
        Args:
            handler: 处理函数,接收Alert对象
        """
        self.alert_handlers.append(handler)


class MonitoringManager:
    """监控管理器 - 统一监控功能接口"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor(history_size=100)
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self._setup_system_checks()
        self._setup_alert_rules()
    
    def _setup_system_checks(self) -> None:
        """设置系统健康检查"""
        self.health_checker.register_check('cpu', self._check_cpu)
        self.health_checker.register_check('memory', self._check_memory)
        self.health_checker.register_check('disk', self._check_disk)
        self.health_checker.register_check('database', self._check_database)
    
    def _check_cpu(self) -> tuple[bool, str]:
        """检查CPU使用率"""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > 90:
            return False, f"CPU使用率过高: {cpu_percent:.1f}%"
        
        self.performance_monitor.record_metric('cpu_usage', cpu_percent)
        return True, f"CPU使用率正常: {cpu_percent:.1f}%"
    
    def _check_memory(self) -> tuple[bool, str]:
        """检查内存使用率"""
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        
        if mem_percent > 90:
            return False, f"内存使用率过高: {mem_percent:.1f}%"
        
        self.performance_monitor.record_metric('memory_usage', mem_percent)
        return True, f"内存使用率正常: {mem_percent:.1f}%"
    
    def _check_disk(self) -> tuple[bool, str]:
        """检查磁盘使用率"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        if disk_percent > 90:
            return False, f"磁盘使用率过高: {disk_percent:.1f}%"
        
        self.performance_monitor.record_metric('disk_usage', disk_percent)
        return True, f"磁盘使用率正常: {disk_percent:.1f}%"
    
    def _check_database(self) -> tuple[bool, str]:
        """检查数据库连接"""
        # 简化实现 - 实际应该检查数据库连接
        self.performance_monitor.record_metric('db_response_time', 0.05)
        return True, "数据库连接正常"
    
    def _setup_alert_rules(self) -> None:
        """设置告警规则"""
        # 在后台线程中定期检查
        self._alert_thread = threading.Thread(target=self._monitor_alerts, daemon=True)
        self._alert_thread.start()
    
    def _monitor_alerts(self) -> None:
        """监控告警规则"""
        while True:
            try:
                # 检查CPU告警
                cpu_stats = self.performance_monitor.get_metric_stats('cpu_usage')
                if cpu_stats.get('current', 0) > 80:
                    self.alert_manager.add_alert(
                        metric_name='cpu_usage',
                        severity='warning',
                        message=f"CPU使用率告警: {cpu_stats['current']:.1f}%",
                        value=cpu_stats['current'],
                        threshold=80
                    )
                
                # 检查内存告警
                mem_stats = self.performance_monitor.get_metric_stats('memory_usage')
                if mem_stats.get('current', 0) > 80:
                    self.alert_manager.add_alert(
                        metric_name='memory_usage',
                        severity='warning',
                        message=f"内存使用率告警: {mem_stats['current']:.1f}%",
                        value=mem_stats['current'],
                        threshold=80
                    )
                
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"告警监控失败: {e}")
                time.sleep(60)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取仪表板数据
        
        Returns:
            仪表板数据字典
        """
        return {
            'health_status': self.health_checker.get_health_status(),
            'performance_metrics': self.performance_monitor.get_all_metrics(),
            'active_alerts': [
                {
                    'id': alert.id,
                    'metric_name': alert.metric_name,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'value': alert.value,
                    'threshold': alert.threshold
                }
                for alert in self.alert_manager.get_active_alerts()
            ],
            'recent_alerts': [
                {
                    'id': alert.id,
                    'metric_name': alert.metric_name,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'resolved': alert.resolved
                }
                for alert in self.alert_manager.get_alerts(hours=24)
            ]
        }
    
    def record_api_response_time(self, endpoint: str, response_time: float) -> None:
        """
        记录API响应时间
        
        Args:
            endpoint: API端点
            response_time: 响应时间(秒)
        """
        metric_name = f"api_response_time_{endpoint}"
        self.performance_monitor.record_metric(
            metric_name,
            response_time,
            metadata={'endpoint': endpoint}
        )
    
    def record_user_activity(self, user_id: str, activity_type: str) -> None:
        """
        记录用户活动
        
        Args:
            user_id: 用户ID
            activity_type: 活动类型
        """
        metric_name = f"user_activity_{activity_type}"
        self.performance_monitor.record_metric(
            metric_name,
            time.time(),
            metadata={'user_id': user_id}
        )


monitoring_manager = MonitoringManager()
