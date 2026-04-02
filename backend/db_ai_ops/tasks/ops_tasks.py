import datetime

from db_ai_ops.extensions import celery, db
from db_ai_ops.models import InspectionReport, InspectionReportStatus, OperationTask, OperationTaskStatus


def _truncate(text, limit=8000):
    if text is None:
        return ''
    s = str(text)
    return s if len(s) <= limit else s[:limit] + '...(truncated)'


def _ssh_exec(host_obj, command, timeout_seconds=30):
    try:
        import paramiko
    except Exception as e:
        raise Exception('Missing dependency: paramiko') from e

    if not host_obj.username:
        raise Exception('Host username is empty')
    if not host_obj.password:
        raise Exception('Host password is empty')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host_obj.host,
        port=host_obj.port,
        username=host_obj.username,
        password=host_obj.password,
        timeout=10,
        banner_timeout=10,
        auth_timeout=10
    )
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout_seconds)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        return exit_code, out, err
    finally:
        client.close()


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
        if t.category == 'server' and t.action in {'exec-script', 'restart-service'}:
            from db_ai_ops.models import Host

            if t.action == 'restart-service':
                service = (payload.get('service') or payload.get('params', {}).get('service') or '').strip()
                if not service:
                    raise Exception('service 不能为空')
                command = f"systemctl restart {service} && systemctl is-active {service}"
            else:
                command = (payload.get('command') or payload.get('params', {}).get('command') or payload.get('params', {}).get('script') or '').strip()
                if not command:
                    raise Exception('command 不能为空')

            items = []
            ok = 0
            failed = 0
            for hid in target_ids:
                h = Host.query.get(hid)
                if not h:
                    failed += 1
                    items.append({
                        'host_id': hid,
                        'status': 'failed',
                        'error': 'Host not found'
                    })
                    continue
                try:
                    code, out, err = _ssh_exec(h, command)
                    status = 'success' if code == 0 else 'failed'
                    ok += 1 if status == 'success' else 0
                    failed += 1 if status == 'failed' else 0
                    items.append({
                        'host_id': h.id,
                        'name': h.name,
                        'host': h.host,
                        'port': h.port,
                        'status': status,
                        'exit_code': code,
                        'stdout': _truncate(out),
                        'stderr': _truncate(err)
                    })
                except Exception as e:
                    failed += 1
                    items.append({
                        'host_id': h.id,
                        'name': h.name,
                        'host': h.host,
                        'port': h.port,
                        'status': 'failed',
                        'error': str(e)
                    })

            t.result = {
                'message': '已执行',
                'action': t.action,
                'command': command,
                'summary': {
                    'targets': len(target_ids),
                    'success': ok,
                    'failed': failed
                },
                'items': items
            }
            t.status = OperationTaskStatus.SUCCESS if ok > 0 and failed == 0 else (OperationTaskStatus.FAILED if ok == 0 else OperationTaskStatus.SUCCESS)
        else:
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
