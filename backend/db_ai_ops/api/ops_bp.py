from flask import Blueprint, jsonify, request, g

from db_ai_ops.extensions import db
from db_ai_ops.models import OperationTask, OperationTaskStatus
from db_ai_ops.tasks.ops_tasks import run_operation_task

ops_bp = Blueprint('ops_bp', __name__)


def _is_admin():
    return 'admin' in (getattr(g, 'current_roles', []) or [])


@ops_bp.route('/ops/deployments/mysql/options', methods=['GET'])
def mysql_deployment_options():
    return jsonify({
        'database_type': 'mysql',
        'topologies': [
            {'value': 'single-node', 'label': '单节点', 'min_hosts': 1, 'max_hosts': 1},
            {'value': 'master-slave', 'label': '一主多从', 'min_hosts': 2, 'max_hosts': None},
            {'value': 'mgr', 'label': 'MySQL 组复制（MGR）', 'min_hosts': 3, 'max_hosts': 9}
        ],
        'versions': ['5.7.x', '8.0.x', '8.4.x'],
        'requires': ['管理员权限', '已启用 Linux 主机', '每台主机的 SSH 凭据', 'DB_PASSWORD 或 GENERIC 初始化凭据', '明确确认 confirmed=true'],
        'safety': {
            'host_key_checking': True,
            'host_hardening': 'disabled',
            'plaintext_password_in_payload': 'rejected'
        }
    })


@ops_bp.route('/ops/tasks', methods=['GET'])
def list_tasks():
    tasks = OperationTask.query.order_by(OperationTask.created_at.desc()).all()
    return jsonify({'tasks': [t.to_dict() for t in tasks]})


@ops_bp.route('/ops/tasks', methods=['POST'])
def create_task():
    data = request.get_json() or {}
    category = (data.get('category') or '').strip()
    action = (data.get('action') or '').strip()

    if not category or not action:
        return jsonify({'error': 'category 和 action 不能为空'}), 400

    payload = data.get('payload') or {}
    if category == 'database' and action == 'mysql-deploy':
        if not _is_admin():
            return jsonify({'error': '仅管理员可以发起数据库部署'}), 403
        if any(key in payload for key in ('password', 'mysql_admin_password', 'ssh_password')):
            return jsonify({'error': '部署请求不得包含明文密码，请使用凭据 ID'}), 400

    t = OperationTask(
        category=category,
        action=action,
        payload=payload,
        status=OperationTaskStatus.PENDING,
        created_by=getattr(g, 'current_user', None)
    )
    db.session.add(t)
    db.session.commit()

    try:
        run_operation_task.delay(t.id)
    except Exception:
        run_operation_task.apply(args=[t.id])
    return jsonify(t.to_dict()), 201


@ops_bp.route('/ops/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    t = OperationTask.query.get_or_404(task_id)
    return jsonify(t.to_dict())
