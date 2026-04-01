from flask import Blueprint, jsonify, request, g

from db_ai_ops.extensions import db
from db_ai_ops.models import InspectionReport, InspectionReportStatus
from db_ai_ops.tasks.ops_tasks import run_inspection_report

inspection_bp = Blueprint('inspection_bp', __name__)


@inspection_bp.route('/inspection/run', methods=['POST'])
def run_inspection():
    data = request.get_json() or {}
    scope = (data.get('scope') or '').strip()
    if not scope:
        return jsonify({'error': 'scope 不能为空'}), 400

    target_ids = data.get('target_ids') or []
    summary = f"{scope}:{len(target_ids)}"

    r = InspectionReport(
        scope=scope,
        target_summary=summary,
        status=InspectionReportStatus.PENDING,
        created_by=getattr(g, 'current_user', None)
    )
    db.session.add(r)
    db.session.commit()

    try:
        run_inspection_report.delay(r.id, data)
    except Exception:
        run_inspection_report.apply(args=[r.id, data])
    return jsonify(r.to_dict()), 201


@inspection_bp.route('/inspection/reports', methods=['GET'])
def list_reports():
    reports = InspectionReport.query.order_by(InspectionReport.created_at.desc()).all()
    return jsonify({'reports': [r.to_dict() for r in reports]})


@inspection_bp.route('/inspection/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    r = InspectionReport.query.get_or_404(report_id)
    return jsonify(r.to_dict())
