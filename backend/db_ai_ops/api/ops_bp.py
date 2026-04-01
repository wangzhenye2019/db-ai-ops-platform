from flask import Blueprint, jsonify, request, g

from db_ai_ops.extensions import db
from db_ai_ops.models import OperationTask, OperationTaskStatus
from db_ai_ops.tasks.ops_tasks import run_operation_task

ops_bp = Blueprint('ops_bp', __name__)


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

    t = OperationTask(
        category=category,
        action=action,
        payload=data.get('payload') or {},
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
