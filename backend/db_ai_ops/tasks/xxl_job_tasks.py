import datetime
import json
import os

from db_ai_ops.config import Config
from db_ai_ops.extensions import celery, db
from db_ai_ops.models import XxlJobTrigger
from db_ai_ops.xxl_job.admin_client import send_callback
from db_ai_ops.xxl_job.handlers import execute_handler


def _log_path(log_id):
    name = f'log_{int(log_id)}.log'
    return os.path.join(Config.XXL_JOB_LOG_FOLDER, name)


def _append_log(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(text)
        if not text.endswith('\n'):
            f.write('\n')


@celery.task(bind=True)
def xxl_job_execute(self, trigger_id):
    t = XxlJobTrigger.query.get(trigger_id)
    if not t:
        return None

    now = datetime.datetime.utcnow()
    t.status = 'running'
    t.started_at = now
    t.celery_task_id = self.request.id
    if not t.log_file:
        t.log_file = _log_path(t.log_id)
    db.session.commit()

    _append_log(t.log_file, f'[{now.isoformat()}] trigger_id={t.id} job_id={t.job_id} log_id={t.log_id} handler={t.executor_handler}')
    if t.executor_params_raw:
        _append_log(t.log_file, f'params_raw={t.executor_params_raw}')
    if t.executor_params:
        _append_log(t.log_file, f'params={json.dumps(t.executor_params, ensure_ascii=False)}')

    handle_code = 200
    handle_msg = ''
    try:
        result = execute_handler(t.executor_handler, t.executor_params or {})
        handle_msg = '' if result is None else str(result)
        _append_log(t.log_file, f'result={handle_msg}')
    except Exception as e:
        handle_code = 500
        handle_msg = str(e)
        _append_log(t.log_file, f'error={handle_msg}')
    finally:
        finished = datetime.datetime.utcnow()
        t.handle_code = handle_code
        t.handle_msg = handle_msg
        t.status = 'success' if handle_code == 200 else 'failed'
        t.finished_at = finished
        db.session.commit()
        _append_log(t.log_file, f'[{finished.isoformat()}] finished status={t.status} handle_code={handle_code}')

        admin_addresses = getattr(Config, 'XXL_JOB_ADMIN_ADDRESSES', None)
        access_token = getattr(Config, 'XXL_JOB_ACCESS_TOKEN', None)
        if admin_addresses:
            try:
                send_callback(
                    admin_addresses=admin_addresses,
                    access_token=access_token,
                    log_id=t.log_id,
                    log_datetime=t.log_datetime or 0,
                    handle_code=handle_code,
                    handle_msg=handle_msg
                )
            except Exception as e:
                _append_log(t.log_file, f'callback_error={str(e)}')

    return handle_msg
