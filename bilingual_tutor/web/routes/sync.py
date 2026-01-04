from flask import Blueprint, request, jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__)


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


@sync_bp.route('/api/sync/status', methods=['GET'])
@require_auth
def get_sync_status():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        db_path = request.args.get('db_path', 'bilingual_tutor/storage/learning.db')
        manager = SyncManager(db_path)
        status = manager.get_sync_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/queue', methods=['POST'])
@require_auth
def queue_sync_operation():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        data = request.get_json()
        db_path = data.get('db_path', 'bilingual_tutor/storage/learning.db')
        
        manager = SyncManager(db_path)
        
        operation_type = data.get('operation_type')
        table_name = data.get('table_name')
        record_id = data.get('record_id')
        sync_data = data.get('data')
        
        if not all([operation_type, table_name, sync_data]):
            return jsonify({'error': 'operation_type, table_name, and data required'}), 400
        
        sync_id = manager.queue_operation(
            operation_type,
            table_name,
            record_id,
            sync_data
        )
        
        return jsonify({
            'success': True,
            'sync_id': sync_id,
            'message': 'Operation queued successfully'
        })
    except Exception as e:
        logger.error(f"Error queuing sync operation: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/sync-all', methods=['POST'])
@require_auth
def sync_all():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        data = request.get_json()
        db_path = data.get('db_path', 'bilingual_tutor/storage/learning.db')
        
        manager = SyncManager(db_path)
        success, results = manager.sync_all()
        
        return jsonify({
            'success': success,
            'results': results
        })
    except Exception as e:
        logger.error(f"Error syncing all: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/retry', methods=['POST'])
@require_auth
def retry_failed():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        data = request.get_json()
        db_path = data.get('db_path', 'bilingual_tutor/storage/learning.db')
        
        manager = SyncManager(db_path)
        success, results = manager.retry_failed_operations()
        
        return jsonify({
            'success': success,
            'results': results
        })
    except Exception as e:
        logger.error(f"Error retrying failed operations: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/clear-failed', methods=['POST'])
@require_auth
def clear_failed():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        data = request.get_json()
        db_path = data.get('db_path', 'bilingual_tutor/storage/learning.db')
        
        manager = SyncManager(db_path)
        deleted_count = manager.clear_failed_operations()
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleared {deleted_count} failed operations'
        })
    except Exception as e:
        logger.error(f"Error clearing failed operations: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/log', methods=['GET'])
@require_auth
def get_sync_log():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        db_path = request.args.get('db_path', 'bilingual_tutor/storage/learning.db')
        limit = int(request.args.get('limit', 100))
        
        manager = SyncManager(db_path)
        log = manager.get_sync_log(limit)
        
        return jsonify({
            'success': True,
            'log': log
        })
    except Exception as e:
        logger.error(f"Error getting sync log: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/conflicts', methods=['GET'])
@require_auth
def get_conflicts():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        db_path = request.args.get('db_path', 'bilingual_tutor/storage/learning.db')
        
        manager = SyncManager(db_path)
        conflicts = manager.get_conflicts()
        
        return jsonify({
            'success': True,
            'conflicts': conflicts
        })
    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/resolve-conflict', methods=['POST'])
@require_auth
def resolve_conflict():
    try:
        from ...infrastructure.sync_manager import SyncManager
        
        data = request.get_json()
        db_path = data.get('db_path', 'bilingual_tutor/storage/learning.db')
        
        table_name = data.get('table_name')
        record_id = data.get('record_id')
        resolution = data.get('resolution')
        
        if not all([table_name, record_id, resolution]):
            return jsonify({'error': 'table_name, record_id, and resolution required'}), 400
        
        manager = SyncManager(db_path)
        success = manager.resolve_conflict(table_name, record_id, resolution)
        
        return jsonify({
            'success': success,
            'message': 'Conflict resolved successfully' if success else 'Failed to resolve conflict'
        })
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}")
        return jsonify({'error': str(e)}), 500
