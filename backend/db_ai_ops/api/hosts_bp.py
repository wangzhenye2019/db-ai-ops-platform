from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Host, HostOSType

hosts_bp = Blueprint('hosts_bp', __name__)


@hosts_bp.route('/hosts', methods=['GET'])
def list_hosts():
    hosts = Host.query.order_by(Host.created_at.desc()).all()
    return jsonify({'hosts': [h.to_dict() for h in hosts]})


@hosts_bp.route('/hosts', methods=['POST'])
def create_host():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    host = (data.get('host') or '').strip()

    if not name or not host:
        return jsonify({'error': 'name 和 host 不能为空'}), 400

    port = int(data.get('port') or 22)
    os_type_raw = (data.get('os_type') or 'linux').lower()
    try:
        os_type = HostOSType(os_type_raw)
    except ValueError:
        return jsonify({'error': f'Invalid os_type. Must be one of: {[e.value for e in HostOSType]}'}), 400

    h = Host(
        name=name,
        host=host,
        port=port,
        os_type=os_type,
        username=data.get('username'),
        password=data.get('password'),
        enabled=bool(data.get('enabled', True)),
        tags=data.get('tags') or []
    )
    db.session.add(h)
    db.session.commit()
    return jsonify(h.to_dict()), 201


@hosts_bp.route('/hosts/<int:host_id>', methods=['GET'])
def get_host(host_id):
    h = Host.query.get_or_404(host_id)
    return jsonify(h.to_dict())


@hosts_bp.route('/hosts/<int:host_id>', methods=['PUT'])
def update_host(host_id):
    h = Host.query.get_or_404(host_id)
    data = request.get_json() or {}

    for field in ['name', 'host', 'username', 'password']:
        if field in data:
            setattr(h, field, data[field])

    if 'port' in data:
        h.port = int(data['port'])

    if 'os_type' in data:
        os_type_raw = (data.get('os_type') or '').lower()
        try:
            h.os_type = HostOSType(os_type_raw)
        except ValueError:
            return jsonify({'error': 'Invalid os_type'}), 400

    if 'enabled' in data:
        h.enabled = bool(data['enabled'])

    if 'tags' in data:
        h.tags = data.get('tags') or []

    db.session.commit()
    return jsonify(h.to_dict())


@hosts_bp.route('/hosts/<int:host_id>', methods=['DELETE'])
def delete_host(host_id):
    h = Host.query.get_or_404(host_id)
    db.session.delete(h)
    db.session.commit()
    return jsonify({'message': 'Host deleted'})


@hosts_bp.route('/hosts/os-types', methods=['GET'])
def host_os_types():
    return jsonify({
        'types': [{'value': e.value, 'label': e.value.upper()} for e in HostOSType]
    })
