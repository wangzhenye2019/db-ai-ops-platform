from flask import Blueprint, current_app, jsonify, request, g

from db_ai_ops.crypto import decrypt_text, encrypt_text
from db_ai_ops.extensions import db
from db_ai_ops.models import Credential, CredentialType

creds_bp = Blueprint('creds_bp', __name__)


def _is_admin():
    roles = getattr(g, 'current_roles', []) or []
    return 'admin' in roles


@creds_bp.route('/credentials/types', methods=['GET'])
def credential_types():
    return jsonify({
        'types': [{'value': e.value, 'label': e.value.upper()} for e in CredentialType]
    })


@creds_bp.route('/credentials', methods=['GET'])
def list_credentials():
    items = Credential.query.order_by(Credential.created_at.desc()).all()
    return jsonify({'credentials': [c.to_safe_dict() for c in items]})


@creds_bp.route('/credentials', methods=['POST'])
def create_credential():
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name 不能为空'}), 400

    if Credential.query.filter_by(name=name).first():
        return jsonify({'error': '凭据名称已存在'}), 400

    ctype_raw = (data.get('cred_type') or 'generic').strip().lower()
    try:
        ctype = CredentialType(ctype_raw)
    except ValueError:
        return jsonify({'error': 'Invalid cred_type'}), 400

    secret = data.get('secret') or ''
    if not str(secret):
        return jsonify({'error': 'secret 不能为空'}), 400

    enc = encrypt_text(str(secret), current_app.config['SECRET_KEY'])

    c = Credential(
        name=name,
        cred_type=ctype,
        username=(data.get('username') or '').strip() or None,
        secret_encrypted=enc,
        business_system_id=int(data['business_system_id']) if data.get('business_system_id') else None,
        owner=(data.get('owner') or '').strip() or None,
        tags=data.get('tags') or [],
        enabled=bool(data.get('enabled', True))
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_safe_dict()), 201


@creds_bp.route('/credentials/<int:cred_id>', methods=['GET'])
def get_credential(cred_id):
    c = Credential.query.get_or_404(cred_id)
    include_secret = request.args.get('include_secret', '0') == '1'
    out = c.to_safe_dict()
    if include_secret and _is_admin():
        out['secret'] = decrypt_text(c.secret_encrypted, current_app.config['SECRET_KEY'])
    return jsonify(out)


@creds_bp.route('/credentials/<int:cred_id>', methods=['PUT'])
def update_credential(cred_id):
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403

    c = Credential.query.get_or_404(cred_id)
    data = request.get_json() or {}

    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name 不能为空'}), 400
        if Credential.query.filter(Credential.name == name, Credential.id != c.id).first():
            return jsonify({'error': '凭据名称已存在'}), 400
        c.name = name

    if 'cred_type' in data:
        try:
            c.cred_type = CredentialType((data.get('cred_type') or '').strip().lower())
        except ValueError:
            return jsonify({'error': 'Invalid cred_type'}), 400

    for field in ['username', 'owner']:
        if field in data:
            val = (data.get(field) or '').strip()
            setattr(c, field, val or None)

    if 'business_system_id' in data:
        c.business_system_id = int(data['business_system_id']) if data.get('business_system_id') else None

    if 'tags' in data:
        c.tags = data.get('tags') or []

    if 'enabled' in data:
        c.enabled = bool(data['enabled'])

    if 'secret' in data and str(data.get('secret') or ''):
        c.secret_encrypted = encrypt_text(str(data['secret']), current_app.config['SECRET_KEY'])

    db.session.commit()
    return jsonify(c.to_safe_dict())


@creds_bp.route('/credentials/<int:cred_id>', methods=['DELETE'])
def delete_credential(cred_id):
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403

    c = Credential.query.get_or_404(cred_id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message': 'Credential deleted'})

