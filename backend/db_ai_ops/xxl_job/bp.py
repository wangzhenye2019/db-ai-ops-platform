import datetime
import os

from flask import Blueprint, current_app, jsonify, request

from db_ai_ops.extensions import celery, db
from db_ai_ops.models import XxlJobTrigger
from db_ai_ops.tasks.xxl_job_tasks import xxl_job_execute
from db_ai_ops.xxl_job.handlers import list_handlers
from db_ai_ops.xxl_job.protocol import parse_executor_params, require_access_token, return_t


xxl_job_bp = Blueprint('xxl_job', __name__)


def _token_ok():
    token = current_app.config.get('XXL_JOB_ACCESS_TOKEN')
    return require_access_token(request, token)


@xxl_job_bp.post('/beat')
def beat():
    if not _token_ok():
        return jsonify(return_t(401, 'Unauthorized')), 401
    return jsonify(return_t(200, None, 'OK'))


@xxl_job_bp.post('/idleBeat')
def idle_beat():
    if not _token_ok():
        return jsonify(return_t(401, 'Unauthorized')), 401
    return jsonify(return_t(200, None, 'OK'))


@xxl_job_bp.post('/run')
def run():
    if not _token_ok():
        return jsonify(return_t(401, 'Unauthorized')), 401

    body = request.get_json(silent=True) or {}
    handler = (body.get('executorHandler') or '').strip()
    if not handler:
        return jsonify(return_t(500, 'executorHandler 不能为空')), 200

    params, params_raw = parse_executor_params(body.get('executorParams'))

    job_id = body.get('jobId')
    log_id = body.get('logId')
    log_datetime = body.get('logDateTime')
    if log_id is None:
        return jsonify(return_t(500, 'logId 不能为空')), 200

    log_file_folder = current_app.config.get('XXL_JOB_LOG_FOLDER') or ''
    log_file = os.path.join(log_file_folder, f'log_{int(log_id)}.log') if log_file_folder else None

    t = XxlJobTrigger(
        job_id=int(job_id) if job_id is not None and str(job_id).strip() != '' else None,
        log_id=int(log_id),
        log_datetime=int(log_datetime) if log_datetime is not None and str(log_datetime).strip() != '' else None,
        executor_handler=handler,
        executor_params=params if isinstance(params, dict) else {'_': params},
        executor_params_raw=params_raw,
        status='queued',
        created_at=datetime.datetime.utcnow(),
        log_file=log_file
    )
    db.session.add(t)
    db.session.commit()

    timeout = body.get('executorTimeout')
    time_limit = None
    try:
        if timeout is not None and str(timeout).strip() != '':
            time_limit = int(timeout)
    except Exception:
        time_limit = None

    kwargs = {}
    if time_limit and time_limit > 0:
        kwargs['time_limit'] = time_limit

    async_result = xxl_job_execute.apply_async(args=[t.id], **kwargs)
    t.celery_task_id = async_result.id
    db.session.commit()

    return jsonify(return_t(200, None, 'OK'))


@xxl_job_bp.post('/kill')
def kill():
    if not _token_ok():
        return jsonify(return_t(401, 'Unauthorized')), 401

    body = request.get_json(silent=True) or {}
    job_id = body.get('jobId')
    log_id = body.get('logId')

    q = XxlJobTrigger.query
    if log_id is not None and str(log_id).strip() != '':
        q = q.filter_by(log_id=int(log_id))
    elif job_id is not None and str(job_id).strip() != '':
        q = q.filter_by(job_id=int(job_id)).order_by(XxlJobTrigger.id.desc())
    else:
        return jsonify(return_t(500, 'jobId/logId 不能为空')), 200

    t = q.first()
    if not t or not t.celery_task_id:
        return jsonify(return_t(200, None, 'OK'))

    try:
        celery.control.revoke(t.celery_task_id, terminate=True)
        t.status = 'killed'
        t.finished_at = datetime.datetime.utcnow()
        db.session.commit()
        return jsonify(return_t(200, None, 'OK'))
    except Exception as e:
        return jsonify(return_t(500, str(e))), 200


@xxl_job_bp.post('/log')
def log():
    if not _token_ok():
        return jsonify(return_t(401, 'Unauthorized')), 401

    body = request.get_json(silent=True) or {}
    log_id = body.get('logId')
    from_line = body.get('fromLineNum') or 1
    try:
        log_id = int(log_id)
        from_line = int(from_line)
    except Exception:
        return jsonify(return_t(500, 'logId/fromLineNum 非法')), 200

    t = XxlJobTrigger.query.filter_by(log_id=log_id).first()
    path = (t.log_file if t else None) or (current_app.config.get('XXL_JOB_LOG_FOLDER') or '')
    if path and os.path.isdir(path):
        path = os.path.join(path, f'log_{log_id}.log')
    if not path or not os.path.exists(path):
        content = {'fromLineNum': from_line, 'toLineNum': from_line, 'logContent': '', 'isEnd': True}
        return jsonify(return_t(200, None, content))

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.read().splitlines()

    start = max(from_line - 1, 0)
    chunk = lines[start:start + 200]
    to_line = start + len(chunk)
    is_end = to_line >= len(lines)
    content = {
        'fromLineNum': from_line,
        'toLineNum': to_line,
        'logContent': '\n'.join(chunk),
        'isEnd': is_end
    }
    return jsonify(return_t(200, None, content))


@xxl_job_bp.get('/handlers')
def handlers():
    if not _token_ok():
        return jsonify(return_t(401, 'Unauthorized')), 401
    return jsonify(return_t(200, None, list_handlers()))


__all__ = ['xxl_job_bp']
