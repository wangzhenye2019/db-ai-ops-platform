from flask import Blueprint, jsonify, request
from sqlalchemy import func

from db_ai_ops.extensions import db
from db_ai_ops.models import AssetSystemLink, AssetType, BusinessContact, BusinessSystem, Database, Host, IpAsset, Middleware

systems_bp = Blueprint('systems_bp', __name__)


@systems_bp.route('/systems', methods=['GET'])
def list_systems():
    systems = BusinessSystem.query.order_by(BusinessSystem.created_at.desc()).all()
    ids = [s.id for s in systems]

    host_counts = {}
    db_counts = {}
    mw_counts = {}
    ip_counts = {}
    link_counts = {}
    if ids:
        host_counts = dict(db.session.query(Host.business_system_id, func.count(Host.id)).filter(Host.business_system_id.in_(ids)).group_by(Host.business_system_id).all())
        db_counts = dict(db.session.query(Database.business_system_id, func.count(Database.id)).filter(Database.business_system_id.in_(ids)).group_by(Database.business_system_id).all())
        mw_counts = dict(db.session.query(Middleware.business_system_id, func.count(Middleware.id)).filter(Middleware.business_system_id.in_(ids)).group_by(Middleware.business_system_id).all())
        ip_counts = dict(db.session.query(IpAsset.business_system_id, func.count(IpAsset.id)).filter(IpAsset.business_system_id.in_(ids)).group_by(IpAsset.business_system_id).all())
        rows = (
            db.session.query(AssetSystemLink.system_id, AssetSystemLink.asset_type, func.count(AssetSystemLink.id))
            .filter(AssetSystemLink.system_id.in_(ids))
            .group_by(AssetSystemLink.system_id, AssetSystemLink.asset_type)
            .all()
        )
        link_counts = {(sid, atype): cnt for sid, atype, cnt in rows}

    return jsonify({
        'systems': [
            {
                **s.to_dict(),
                'counts': {
                    'hosts': int(host_counts.get(s.id, 0) or 0) + int(link_counts.get((s.id, AssetType.HOST), 0) or 0),
                    'databases': int(db_counts.get(s.id, 0) or 0) + int(link_counts.get((s.id, AssetType.DATABASE), 0) or 0),
                    'middlewares': int(mw_counts.get(s.id, 0) or 0) + int(link_counts.get((s.id, AssetType.MIDDLEWARE), 0) or 0),
                    'ips': int(ip_counts.get(s.id, 0) or 0) + int(link_counts.get((s.id, AssetType.IP), 0) or 0)
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
    links = AssetSystemLink.query.filter_by(system_id=s.id).all()
    link_ids = {}
    for l in links:
        link_ids.setdefault(l.asset_type, set()).add(l.asset_id)

    hosts = Host.query.order_by(Host.created_at.desc()).all()
    hosts = [h for h in hosts if h.business_system_id == s.id or h.id in link_ids.get(AssetType.HOST, set())]

    dbs = Database.query.order_by(Database.created_at.desc()).all()
    dbs = [d for d in dbs if d.business_system_id == s.id or d.id in link_ids.get(AssetType.DATABASE, set())]

    mws = Middleware.query.order_by(Middleware.created_at.desc()).all()
    mws = [m for m in mws if m.business_system_id == s.id or m.id in link_ids.get(AssetType.MIDDLEWARE, set())]

    ips = IpAsset.query.order_by(IpAsset.created_at.desc()).all()
    ips = [i for i in ips if i.business_system_id == s.id or i.id in link_ids.get(AssetType.IP, set())]
    return jsonify({
        'system': s.to_dict(),
        'hosts': [h.to_dict() for h in hosts],
        'databases': [d.to_dict() for d in dbs],
        'middlewares': [m.to_dict() for m in mws],
        'ips': [i.to_dict() for i in ips]
    })


@systems_bp.route('/systems/<int:system_id>/links', methods=['GET'])
def list_links(system_id):
    BusinessSystem.query.get_or_404(system_id)
    links = AssetSystemLink.query.filter_by(system_id=system_id).order_by(AssetSystemLink.created_at.desc()).all()
    return jsonify({'links': [l.to_dict() for l in links]})


@systems_bp.route('/systems/<int:system_id>/links', methods=['POST'])
def update_links(system_id):
    BusinessSystem.query.get_or_404(system_id)
    data = request.get_json() or {}
    add = data.get('add') or []
    remove = data.get('remove') or []

    added = 0
    removed = 0
    errors = []

    def _parse_type(v):
        try:
            return AssetType(str(v).strip().lower())
        except ValueError:
            return None

    for item in add:
        try:
            a_type = _parse_type(item.get('type'))
            a_id = int(item.get('id'))
            if not a_type:
                raise ValueError('Invalid type')
            if a_type == AssetType.HOST:
                obj = Host.query.get(a_id)
                if not obj:
                    raise ValueError('Host not found')
                if obj.business_system_id == system_id:
                    continue
            elif a_type == AssetType.DATABASE:
                obj = Database.query.get(a_id)
                if not obj:
                    raise ValueError('Database not found')
                if obj.business_system_id == system_id:
                    continue
            elif a_type == AssetType.MIDDLEWARE:
                obj = Middleware.query.get(a_id)
                if not obj:
                    raise ValueError('Middleware not found')
                if obj.business_system_id == system_id:
                    continue
            elif a_type == AssetType.IP:
                obj = IpAsset.query.get(a_id)
                if not obj:
                    raise ValueError('IP not found')
                if obj.business_system_id == system_id:
                    continue
            exists = AssetSystemLink.query.filter_by(system_id=system_id, asset_type=a_type, asset_id=a_id).first()
            if exists:
                continue
            db.session.add(AssetSystemLink(system_id=system_id, asset_type=a_type, asset_id=a_id))
            added += 1
        except Exception as e:
            errors.append({'action': 'add', 'item': item, 'error': str(e)})

    for item in remove:
        try:
            a_type = _parse_type(item.get('type'))
            a_id = int(item.get('id'))
            if not a_type:
                raise ValueError('Invalid type')
            link = AssetSystemLink.query.filter_by(system_id=system_id, asset_type=a_type, asset_id=a_id).first()
            if not link:
                continue
            db.session.delete(link)
            removed += 1
        except Exception as e:
            errors.append({'action': 'remove', 'item': item, 'error': str(e)})

    db.session.commit()
    return jsonify({'added': added, 'removed': removed, 'errors': errors})


@systems_bp.route('/systems/<int:system_id>/contacts', methods=['GET'])
def list_contacts(system_id):
    s = BusinessSystem.query.get_or_404(system_id)
    items = BusinessContact.query.filter_by(system_id=s.id).order_by(BusinessContact.created_at.desc()).all()
    return jsonify({'system': s.to_dict(), 'contacts': [c.to_dict() for c in items]})


@systems_bp.route('/systems/<int:system_id>/contacts', methods=['POST'])
def create_contact(system_id):
    s = BusinessSystem.query.get_or_404(system_id)
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name 不能为空'}), 400
    c = BusinessContact(
        system_id=s.id,
        name=name,
        role=(data.get('role') or '').strip() or None,
        phone=(data.get('phone') or '').strip() or None,
        email=(data.get('email') or '').strip() or None,
        remark=(data.get('remark') or '').strip() or None
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@systems_bp.route('/systems/<int:system_id>/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(system_id, contact_id):
    BusinessSystem.query.get_or_404(system_id)
    c = BusinessContact.query.get_or_404(contact_id)
    if c.system_id != system_id:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message': 'Contact deleted'})
