from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Middleware, MiddlewareType

middleware_bp = Blueprint('middleware_bp', __name__)


@middleware_bp.route('/middlewares', methods=['GET'])
def list_middlewares():
    items = Middleware.query.order_by(Middleware.created_at.desc()).all()
    return jsonify({'middlewares': [m.to_dict() for m in items]})


@middleware_bp.route('/middlewares', methods=['POST'])
def create_middleware():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    host = (data.get('host') or '').strip()
    port = data.get('port')

    if not name or not host or port is None:
        return jsonify({'error': 'name、host、port 不能为空'}), 400

    mw_type_raw = (data.get('mw_type') or 'other').lower()
    try:
        mw_type = MiddlewareType(mw_type_raw)
    except ValueError:
        return jsonify({'error': f'Invalid mw_type. Must be one of: {[e.value for e in MiddlewareType]}'}), 400

    m = Middleware(
        name=name,
        mw_type=mw_type,
        host=host,
        port=int(port),
        version=(data.get('version') or '').strip() or None,
        business_system_id=int(data['business_system_id']) if data.get('business_system_id') else None,
        owner=(data.get('owner') or '').strip() or None,
        env=(data.get('env') or '').strip() or None,
        remark=(data.get('remark') or '').strip() or None,
        enabled=bool(data.get('enabled', True)),
        meta=data.get('meta') or {}
    )
    db.session.add(m)
    db.session.commit()
    return jsonify(m.to_dict()), 201


@middleware_bp.route('/middlewares/<int:mw_id>', methods=['GET'])
def get_middleware(mw_id):
    m = Middleware.query.get_or_404(mw_id)
    return jsonify(m.to_dict())


@middleware_bp.route('/middlewares/<int:mw_id>', methods=['PUT'])
def update_middleware(mw_id):
    m = Middleware.query.get_or_404(mw_id)
    data = request.get_json() or {}

    for field in ['name', 'host', 'version', 'owner', 'env', 'remark']:
        if field in data:
            val = data[field]
            if isinstance(val, str):
                val = val.strip()
            setattr(m, field, val or None)

    if 'port' in data:
        m.port = int(data['port'])

    if 'mw_type' in data:
        mw_type_raw = (data.get('mw_type') or '').lower()
        try:
            m.mw_type = MiddlewareType(mw_type_raw)
        except ValueError:
            return jsonify({'error': 'Invalid mw_type'}), 400

    if 'enabled' in data:
        m.enabled = bool(data['enabled'])

    if 'meta' in data:
        m.meta = data.get('meta') or {}

    if 'business_system_id' in data:
        m.business_system_id = int(data['business_system_id']) if data.get('business_system_id') else None

    db.session.commit()
    return jsonify(m.to_dict())


@middleware_bp.route('/middlewares/<int:mw_id>', methods=['DELETE'])
def delete_middleware(mw_id):
    m = Middleware.query.get_or_404(mw_id)
    db.session.delete(m)
    db.session.commit()
    return jsonify({'message': 'Middleware deleted'})


@middleware_bp.route('/middlewares/types', methods=['GET'])
def middleware_types():
    return jsonify({
        'types': [{'value': e.value, 'label': e.value.upper()} for e in MiddlewareType]
    })
