import datetime

from db_ai_ops.extensions import celery, db
from db_ai_ops.models import InspectionReport, InspectionReportStatus, OperationTask, OperationTaskStatus


@celery.task
def run_operation_task(task_id):
    t = OperationTask.query.get(task_id)
    if not t:
        return

    t.status = OperationTaskStatus.RUNNING
    t.started_at = datetime.datetime.utcnow()
    db.session.commit()

    try:
        payload = t.payload or {}
        target_ids = payload.get('target_ids') or []
        t.result = {
            'message': '任务已执行（演示模式）',
            'target_count': len(target_ids),
            'payload': payload
        }
        t.status = OperationTaskStatus.SUCCESS
        t.completed_at = datetime.datetime.utcnow()
        db.session.commit()
    except Exception as e:
        t.status = OperationTaskStatus.FAILED
        t.error_message = str(e)
        t.completed_at = datetime.datetime.utcnow()
        db.session.commit()
        raise


@celery.task
def run_inspection_report(report_id, request_payload=None):
    r = InspectionReport.query.get(report_id)
    if not r:
        return

    r.status = InspectionReportStatus.RUNNING
    db.session.commit()

    try:
        payload = request_payload or {}
        target_ids = payload.get('target_ids') or []
        items = []
        for idx, tid in enumerate(target_ids[:50], start=1):
            items.append({
                'id': tid,
                'name': f'target-{tid}',
                'status': 'ok',
                'score': 100,
                'checks': [
                    {'key': 'connectivity', 'status': 'ok', 'message': 'reachable'},
                    {'key': 'resource', 'status': 'ok', 'message': 'normal'}
                ]
            })

        r.result = {
            'scope': r.scope,
            'generated_at': datetime.datetime.utcnow().isoformat(),
            'summary': {
                'targets': len(target_ids),
                'ok': len(items),
                'warning': 0,
                'critical': 0
            },
            'items': items
        }
        r.status = InspectionReportStatus.READY
        r.completed_at = datetime.datetime.utcnow()
        db.session.commit()
    except Exception as e:
        r.status = InspectionReportStatus.FAILED
        r.error_message = str(e)
        r.completed_at = datetime.datetime.utcnow()
        db.session.commit()
        raise
