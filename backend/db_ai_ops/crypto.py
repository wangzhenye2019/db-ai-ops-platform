import base64
import hashlib
import os


def _derive_key_from_secret(secret) -> bytes:
    if secret is None:
        raw = b''
    elif isinstance(secret, bytes):
        raw = secret
    else:
        raw = str(secret).encode('utf-8')
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet_key(secret_key) -> bytes:
    raw = (os.getenv('CREDENTIALS_FERNET_KEY') or '').strip()
    if raw:
        return raw.encode('utf-8')
    return _derive_key_from_secret(secret_key)


def encrypt_text(plain_text: str, secret_key) -> str:
    from cryptography.fernet import Fernet

    f = Fernet(get_fernet_key(secret_key))
    token = f.encrypt((plain_text or '').encode('utf-8'))
    return token.decode('utf-8')


def decrypt_text(cipher_text: str, secret_key) -> str:
    from cryptography.fernet import Fernet

    f = Fernet(get_fernet_key(secret_key))
    plain = f.decrypt((cipher_text or '').encode('utf-8'))
    return plain.decode('utf-8')
