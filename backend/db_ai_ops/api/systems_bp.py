from flask import Blueprint, jsonify, request
from sqlalchemy import func

from db_ai_ops.extensions import db
from db_ai_ops.models import BusinessSystem, Database, Host, Middleware

systems_bp = Blueprint('systems_bp', __name__)


@systems_bp.route('/systems', methods=['GET'])
def list_systems():
    systems = BusinessSystem.query.order_by(BusinessSystem.created_at.desc()).all()
    ids = [s.id for s in systems]

    host_counts = {}
    db_counts = {}
    mw_counts = {}
    if ids:
        host_counts = dict(db.session.query(Host.business_system_id, func.count(Host.id)).filter(Host.business_system_id.in_(ids)).group_by(Host.business_system_id).all())
        db_counts = dict(db.session.query(Database.business_system_id, func.count(Database.id)).filter(Database.business_system_id.in_(ids)).group_by(Database.business_system_id).all())
        mw_counts = dict(db.session.query(Middleware.business_system_id, func.count(Middleware.id)).filter(Middleware.business_system_id.in_(ids)).group_by(Middleware.business_system_id).all())

    return jsonify({
        'systems': [
            {
                **s.to_dict(),
                'counts': {
                    'hosts': int(host_counts.get(s.id, 0) or 0),
                    'databases': int(db_counts.get(s.id, 0) or 0),
                    'middlewares': int(mw_counts.get(s.id, 0) or 0)
                }
            }
            for s in systems
        ]
    })


@systems_bp.route('/systems', methods=['POST'])
def create_system():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name 不能为空'}), 400
    if BusinessSystem.query.filter_by(name=name).first():
        return jsonify({'error': '业务系统名称已存在'}), 400

    code = (data.get('code') or '').strip() or None
    if code and BusinessSystem.query.filter_by(code=code).first():
        return jsonify({'error': '业务系统编码已存在'}), 400

    s = BusinessSystem(
        name=name,
        code=code,
        owner=(data.get('owner') or '').strip() or None,
        owner_contact=(data.get('owner_contact') or '').strip() or None,
        description=(data.get('description') or '').strip() or None,
        tags=data.get('tags') or [],
        enabled=bool(data.get('enabled', True))
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201


@systems_bp.route('/systems/<int:system_id>', methods=['GET'])
def get_system(system_id):
    s = BusinessSystem.query.get_or_404(system_id)
    return jsonify(s.to_dict())


@systems_bp.route('/systems/<int:system_id>', methods=['PUT'])
def update_system(system_id):
    s = BusinessSystem.query.get_or_404(system_id)
    data = request.get_json() or {}

    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name 不能为空'}), 400
        if BusinessSystem.query.filter(BusinessSystem.name == name, BusinessSystem.id != s.id).first():
            return jsonify({'error': '业务系统名称已存在'}), 400
        s.name = name

    if 'code' in data:
        code = (data.get('code') or '').strip() or None
        if code and BusinessSystem.query.filter(BusinessSystem.code == code, BusinessSystem.id != s.id).first():
            return jsonify({'error': '业务系统编码已存在'}), 400
        s.code = code

    for field in ['owner', 'owner_contact', 'description']:
        if field in data:
            val = (data.get(field) or '').strip()
            setattr(s, field, val or None)

    if 'tags' in data:
        s.tags = data.get('tags') or []

    if 'enabled' in data:
        s.enabled = bool(data['enabled'])

    db.session.commit()
    return jsonify(s.to_dict())


@systems_bp.route('/systems/<int:system_id>', methods=['DELETE'])
def delete_system(system_id):
    s = BusinessSystem.query.get_or_404(system_id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({'message': 'System deleted'})


@systems_bp.route('/systems/<int:system_id>/assets', methods=['GET'])
def system_assets(system_id):
    s = BusinessSystem.query.get_or_404(system_id)
    hosts = Host.query.filter_by(business_system_id=s.id).order_by(Host.created_at.desc()).all()
    dbs = Database.query.filter_by(business_system_id=s.id).order_by(Database.created_at.desc()).all()
    mws = Middleware.query.filter_by(business_system_id=s.id).order_by(Middleware.created_at.desc()).all()
    return jsonify({
        'system': s.to_dict(),
        'hosts': [h.to_dict() for h in hosts],
        'databases': [d.to_dict() for d in dbs],
        'middlewares': [m.to_dict() for m in mws]
    })
