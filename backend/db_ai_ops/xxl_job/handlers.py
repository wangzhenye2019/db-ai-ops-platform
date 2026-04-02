import json


def list_handlers():
    return sorted(_HANDLERS.keys())


def execute_handler(handler_name, params):
    h = _HANDLERS.get(handler_name)
    if not h:
        raise Exception(f'Unknown executorHandler: {handler_name}')
    return h(params or {})


def _as_int(v, field):
    if v is None or v == '':
        raise Exception(f'{field} 不能为空')
    try:
        return int(v)
    except Exception as e:
        raise Exception(f'{field} 必须是整数') from e


def _as_json(v, field):
    if v is None or v == '':
        return None
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(str(v))
    except Exception as e:
        raise Exception(f'{field} 必须是 JSON') from e


def _h_backup_database(params):
    from db_ai_ops.tasks.backup_tasks import backup_database

    database_id = _as_int(params.get('database_id') or params.get('id'), 'database_id')
    return backup_database.run(database_id)


def _h_cleanup_old_backups(params):
    from db_ai_ops.tasks.backup_tasks import cleanup_old_backups

    return cleanup_old_backups.run()


def _h_run_operation_task(params):
    from db_ai_ops.tasks.ops_tasks import run_operation_task

    task_id = _as_int(params.get('task_id') or params.get('id'), 'task_id')
    return run_operation_task.run(task_id)


def _h_run_inspection_report(params):
    from db_ai_ops.tasks.ops_tasks import run_inspection_report

    report_id = _as_int(params.get('report_id') or params.get('id'), 'report_id')
    request_payload = _as_json(params.get('request_payload') or params.get('payload'), 'request_payload')
    return run_inspection_report.run(report_id, request_payload=request_payload)


_HANDLERS = {
    'backup_database': _h_backup_database,
    'cleanup_old_backups': _h_cleanup_old_backups,
    'run_operation_task': _h_run_operation_task,
    'run_inspection_report': _h_run_inspection_report
}
