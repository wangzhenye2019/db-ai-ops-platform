import json
import socket
import urllib.error
import urllib.request


class HttpError(Exception):
    def __init__(self, status, body=None):
        super().__init__(f'HTTP {status}')
        self.status = status
        self.body = body


def post_json(url, data, headers=None, timeout=10):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url=url, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    if headers:
        for k, v in headers.items():
            if v is None:
                continue
            req.add_header(k, str(v))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode('utf-8', errors='replace')
            return resp.status, resp_body
    except urllib.error.HTTPError as e:
        resp_body = ''
        try:
            resp_body = e.read().decode('utf-8', errors='replace')
        except Exception:
            pass
        raise HttpError(e.code, resp_body) from e
    except (urllib.error.URLError, socket.timeout) as e:
        raise HttpError(0, str(e)) from e
