"""
Monitoring Routes
监控路由 - 提供性能监控仪表板、健康检查和告警API
"""

from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta

from bilingual_tutor.infrastructure.monitoring_manager import monitoring_manager

monitoring_bp = Blueprint('monitoring', __name__)


@monitoring_bp.route('/monitoring', methods=['GET'])
def monitoring_dashboard():
    """性能监控仪表板页面"""
    return render_template('monitoring.html')


@monitoring_bp.route('/api/monitoring/dashboard', methods=['GET'])
def get_dashboard_data():
    """
    获取仪表板数据
    
    返回健康状态、性能指标和告警信息
    """
    try:
        dashboard_data = monitoring_manager.get_dashboard_data()
        
        return jsonify({
            'success': True,
            'data': dashboard_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取仪表板数据失败: {str(e)}'
        }), 500


@monitoring_bp.route('/api/monitoring/health', methods=['GET'])
def get_health_status():
    """
    获取系统健康状态
    """
    try:
        health_status = monitoring_manager.health_checker.get_health_status()
        
        return jsonify({
            'success': True,
            'status': health_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取健康状态失败: {str(e)}'
        }), 500


@monitoring_bp.route('/api/monitoring/metrics', methods=['GET'])
def get_metrics():
    """
    获取性能指标
    
    Query参数:
        - metric_name: 指标名称(可选)
        - minutes: 时间范围(默认5分钟)
    """
    try:
        metric_name = request.args.get('metric_name')
        minutes = int(request.args.get('minutes', 5))
        
        if metric_name:
            metrics = monitoring_manager.performance_monitor.get_metric(metric_name, minutes)
            stats = monitoring_manager.performance_monitor.get_metric_stats(metric_name, minutes)
            
            return jsonify({
                'success': True,
                'metric_name': metric_name,
                'data': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'value': m.value,
                        'metadata': m.metadata
                    }
                    for m in metrics
                ],
                'stats': stats
            })
        else:
            all_metrics = monitoring_manager.performance_monitor.get_all_metrics()
            
            return jsonify({
                'success': True,
                'metrics': all_metrics
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取性能指标失败: {str(e)}'
        }), 500


@monitoring_bp.route('/api/monitoring/alerts', methods=['GET'])
def get_alerts():
    """
    获取告警列表
    
    Query参数:
        - metric_name: 指标名称筛选(可选)
        - hours: 时间范围(默认24小时)
        - active_only: 仅未解决告警(可选)
    """
    try:
        metric_name = request.args.get('metric_name')
        hours = int(request.args.get('hours', 24))
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        if active_only:
            alerts = monitoring_manager.alert_manager.get_active_alerts()
        else:
            alerts = monitoring_manager.alert_manager.get_alerts(metric_name, hours)
        
        return jsonify({
            'success': True,
            'alerts': [
                {
                    'id': alert.id,
                    'metric_name': alert.metric_name,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'value': alert.value,
                    'threshold': alert.threshold,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
                }
                for alert in alerts
            ],
            'count': len(alerts)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取告警列表失败: {str(e)}'
        }), 500


@monitoring_bp.route('/api/monitoring/alerts/<alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id: str):
    """
    解决告警
    """
    try:
        success = monitoring_manager.alert_manager.resolve_alert(alert_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '告警已解决'
            })
        else:
            return jsonify({
                'success': False,
                'message': '告警不存在或已解决'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'解决告警失败: {str(e)}'
        }), 500


@monitoring_bp.route('/api/monitoring/checks', methods=['GET'])
def get_health_checks():
    """
    获取健康检查列表
    
    Query参数:
        - check_name: 检查名称(可选,如果指定则运行单个检查)
    """
    try:
        check_name = request.args.get('check_name')
        
        if check_name:
            result = monitoring_manager.health_checker.run_check(check_name)
            return jsonify({
                'success': True,
                'check': result
            })
        else:
            results = monitoring_manager.health_checker.run_all_checks()
            return jsonify({
                'success': True,
                'checks': results
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取健康检查失败: {str(e)}'
        }), 500


@monitoring_bp.route('/api/monitoring/metrics/record', methods=['POST'])
def record_custom_metric():
    """
    记录自定义指标
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        metric_name = data.get('metric_name')
        value = data.get('value')
        metadata = data.get('metadata', {})
        
        if not metric_name or value is None:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        monitoring_manager.performance_monitor.record_metric(
            metric_name,
            float(value),
            metadata
        )
        
        return jsonify({
            'success': True,
            'message': '指标已记录'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'记录指标失败: {str(e)}'
        }), 500


@monitoring_bp.route('/api/monitoring/alerts/create', methods=['POST'])
def create_alert():
    """
    创建手动告警
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        metric_name = data.get('metric_name', 'manual')
        severity = data.get('severity', 'info')
        message = data.get('message', '')
        value = data.get('value', 0)
        threshold = data.get('threshold', 0)
        
        if severity not in ['info', 'warning', 'critical']:
            return jsonify({'success': False, 'message': '无效的严重程度'}), 400
        
        if not message:
            return jsonify({'success': False, 'message': '告警消息不能为空'}), 400
        
        alert = monitoring_manager.alert_manager.add_alert(
            metric_name=metric_name,
            severity=severity,
            message=message,
            value=float(value),
            threshold=float(threshold)
        )
        
        return jsonify({
            'success': True,
            'message': '告警已创建',
            'alert': {
                'id': alert.id,
                'metric_name': alert.metric_name,
                'severity': alert.severity,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'创建告警失败: {str(e)}'
        }), 500
