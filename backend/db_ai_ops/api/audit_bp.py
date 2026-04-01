from flask import Blueprint, jsonify, request

from db_ai_ops.models import AuditLog

audit_bp = Blueprint('audit_bp', __name__)


@audit_bp.route('/audit/logs', methods=['GET'])
def list_audit_logs():
    limit = request.args.get('limit', 200, type=int)
    limit = min(max(limit, 1), 500)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({'logs': [l.to_dict() for l in logs]})
