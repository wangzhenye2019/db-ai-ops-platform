import os
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash


def _serializer(secret_key):
    return URLSafeTimedSerializer(secret_key=secret_key, salt='db-ai-ops-auth')


def issue_token(secret_key, username):
    s = _serializer(secret_key)
    return s.dumps({'u': username})


def verify_token(secret_key, token):
    s = _serializer(secret_key)
    try:
        ttl = int(os.getenv('ADMIN_TOKEN_TTL_SECONDS', '86400'))
        data = s.loads(token, max_age=ttl)
        return data.get('u')
    except (BadSignature, SignatureExpired):
        return None


def verify_admin_password(raw_password):
    password_hash = os.getenv('ADMIN_PASSWORD_HASH')
    if password_hash:
        return check_password_hash(password_hash, raw_password)
    password = os.getenv('ADMIN_PASSWORD', 'admin')
    return raw_password == password


def admin_username():
    return os.getenv('ADMIN_USERNAME', 'admin')
