import os

from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Backup, BackupStatus
from db_ai_ops.tasks import backup_database, cleanup_old_backups

backup_bp = Blueprint('backup_bp', __name__)


@backup_bp.route('/backups', methods=['GET'])
def list_backups():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    database_id = request.args.get('database_id', type=int)
    status = request.args.get('status')

    query = Backup.query

    if database_id:
        query = query.filter_by(database_id=database_id)
    if status:
        query = query.filter_by(status=BackupStatus(status))

    query = query.order_by(Backup.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'backups': [backup.to_dict() for backup in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@backup_bp.route('/backups/<int:backup_id>', methods=['GET'])
def get_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)
    return jsonify(backup.to_dict())


@backup_bp.route('/backups', methods=['POST'])
def create_backup():
    data = request.get_json()
    database_id = data.get('database_id')

    if not database_id:
        return jsonify({'error': 'database_id is required'}), 400

    from db_ai_ops.models import Database

    database = Database.query.get(database_id)
    if not database:
        return jsonify({'error': 'Database not found'}), 404
    if not database.enabled:
        return jsonify({'error': 'Database is disabled'}), 400

    result = backup_database.delay(database_id)

    return jsonify({
        'message': 'Backup started',
        'task_id': result.id,
        'database_id': database_id
    }), 201


@backup_bp.route('/backups/<int:backup_id>/download', methods=['GET'])
def download_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)

    if backup.status != BackupStatus.SUCCESS:
        return jsonify({'error': 'Backup not completed'}), 400
    if not backup.file_path:
        return jsonify({'error': 'Backup file not found'}), 404

    return jsonify({
        'file_path': backup.file_path,
        'file_size': backup.file_size
    })


@backup_bp.route('/backups/<int:backup_id>', methods=['DELETE'])
def delete_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)

    if backup.file_path and os.path.exists(backup.file_path):
        try:
            os.remove(backup.file_path)
        except OSError:
            pass

    db.session.delete(backup)
    db.session.commit()

    return jsonify({'message': 'Backup deleted'})


@backup_bp.route('/backups/cleanup', methods=['POST'])
def cleanup_backups():
    result = cleanup_old_backups.delay()
    return jsonify({
        'message': 'Cleanup started',
        'task_id': result.id
    })


@backup_bp.route('/backups/stats', methods=['GET'])
def backup_stats():
    from db_ai_ops.models import Database

    total_databases = Database.query.filter_by(enabled=True).count()
    total_backups = Backup.query.count()
    successful_backups = Backup.query.filter_by(status=BackupStatus.SUCCESS).count()
    failed_backups = Backup.query.filter_by(status=BackupStatus.FAILED).count()

    total_size = db.session.query(db.func.sum(Backup.file_size)).scalar() or 0

    return jsonify({
        'total_databases': total_databases,
        'total_backups': total_backups,
        'successful_backups': successful_backups,
        'failed_backups': failed_backups,
        'total_size_bytes': total_size,
        'total_size_mb': round(total_size / (1024 * 1024), 2)
    })
