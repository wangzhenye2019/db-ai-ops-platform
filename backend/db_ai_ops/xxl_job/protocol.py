import json


def return_t(code=200, msg=None, content=None):
    return {'code': int(code), 'msg': msg, 'content': content}


def parse_executor_params(raw):
    if raw is None:
        return {}, ''
    if isinstance(raw, (dict, list)):
        return raw, json.dumps(raw, ensure_ascii=False)
    s = str(raw).strip()
    if not s:
        return {}, ''
    try:
        v = json.loads(s)
        if isinstance(v, dict):
            return v, s
        return {'_': v}, s
    except Exception:
        pass

    out = {}
    parts = []
    for chunk in s.replace('\n', '&').replace(' ', '&').split('&'):
        c = chunk.strip()
        if not c:
            continue
        parts.append(c)
    for p in parts:
        if '=' not in p:
            out[p] = True
            continue
        k, v = p.split('=', 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        out[k] = v
    return out, s


def require_access_token(request, configured_token):
    token = (configured_token or '').strip()
    if not token:
        return True
    got = (request.headers.get('XXL-JOB-ACCESS-TOKEN') or '').strip()
    return got == token
