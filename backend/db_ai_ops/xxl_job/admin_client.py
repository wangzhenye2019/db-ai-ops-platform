import json

from db_ai_ops.xxl_job.http_client import post_json


def _admin_bases(admin_addresses):
    if not admin_addresses:
        return []
    if isinstance(admin_addresses, str):
        bases = [s.strip() for s in admin_addresses.split(',') if s.strip()]
    else:
        bases = [str(s).strip() for s in admin_addresses if str(s).strip()]
    return [b[:-1] if b.endswith('/') else b for b in bases]


def send_callback(admin_addresses, access_token, log_id, log_datetime, handle_code, handle_msg, timeout=10):
    bases = _admin_bases(admin_addresses)
    if not bases:
        return None
    payload = [{
        'logId': int(log_id),
        'logDateTim': int(log_datetime) if log_datetime is not None else 0,
        'handleCode': int(handle_code),
        'handleMsg': handle_msg or ''
    }]
    headers = {}
    token = (access_token or '').strip()
    if token:
        headers['XXL-JOB-ACCESS-TOKEN'] = token
    last = None
    for base in bases:
        url = f'{base}/api/callback'
        try:
            status, body = post_json(url, payload, headers=headers, timeout=timeout)
            try:
                return status, json.loads(body) if body else None
            except Exception:
                return status, body
        except Exception as e:
            last = e
            continue
    raise last
