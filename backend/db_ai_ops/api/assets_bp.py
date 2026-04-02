from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import (
    AssetGroup,
    AssetGroupMember,
    AssetType,
    Database,
    Host,
    Middleware
)

assets_bp = Blueprint('assets_bp', __name__)


def _parse_asset_type(v):
    if not v:
        return None
    s = str(v).strip().lower()
    try:
        return AssetType(s)
    except ValueError:
        return None


def _asset_label(asset_type, obj):
    if asset_type == AssetType.HOST:
        return f"{obj.name} ({obj.host}:{obj.port})"
    if asset_type == AssetType.DATABASE:
        return f"{obj.name} ({obj.db_type.value}@{obj.host}:{obj.port}/{obj.database})"
    return f"{obj.name} ({obj.mw_type.value}@{obj.host}:{obj.port})"


@assets_bp.route('/assets/summary', methods=['GET'])
def asset_summary():
    return jsonify({
        'counts': {
            'hosts': Host.query.count(),
            'databases': Database.query.count(),
            'middlewares': Middleware.query.count(),
            'groups': AssetGroup.query.count()
        }
    })


@assets_bp.route('/assets', methods=['GET'])
def list_assets():
    q = (request.args.get('q') or '').strip().lower()
    type_raw = request.args.get('type')
    group_id = request.args.get('group_id', type=int)
    system_id = request.args.get('system_id', type=int)

    asset_type = _parse_asset_type(type_raw)
    members_by_type = None
    if group_id:
        group = AssetGroup.query.get_or_404(group_id)
        members = AssetGroupMember.query.filter_by(group_id=group.id).all()
        members_by_type = {}
        for m in members:
            members_by_type.setdefault(m.asset_type, set()).add(m.asset_id)

    def _filter_keyword(item_text):
        if not q:
            return True
        return q in (item_text or '').lower()

    assets = []

    def _append_items(a_type, items):
        ids = None
        if members_by_type is not None:
            ids = members_by_type.get(a_type, set())
        for obj in items:
            if ids is not None and obj.id not in ids:
                continue
            if system_id and getattr(obj, 'business_system_id', None) != system_id:
                continue
            label = _asset_label(a_type, obj)
            if not _filter_keyword(label) and not _filter_keyword(getattr(obj, 'name', '')):
                continue
            data = obj.to_dict()
            assets.append({
                'type': a_type.value,
                'label': label,
                'data': data
            })

    if asset_type in (None, AssetType.HOST):
        hosts = Host.query.order_by(Host.created_at.desc()).all()
        _append_items(AssetType.HOST, hosts)
    if asset_type in (None, AssetType.DATABASE):
        dbs = Database.query.order_by(Database.created_at.desc()).all()
        _append_items(AssetType.DATABASE, dbs)
    if asset_type in (None, AssetType.MIDDLEWARE):
        mws = Middleware.query.order_by(Middleware.created_at.desc()).all()
        _append_items(AssetType.MIDDLEWARE, mws)

    return jsonify({'assets': assets, 'total': len(assets)})


@assets_bp.route('/assets/groups', methods=['GET'])
def list_groups():
    groups = AssetGroup.query.order_by(AssetGroup.created_at.desc()).all()
    group_ids = [g.id for g in groups]
    members = AssetGroupMember.query.filter(AssetGroupMember.group_id.in_(group_ids)).all() if group_ids else []
    counts = {}
    for m in members:
        counts.setdefault(m.group_id, {'host': 0, 'database': 0, 'middleware': 0})
        counts[m.group_id][m.asset_type.value] += 1
    return jsonify({
        'groups': [
            {
                **g.to_dict(),
                'counts': counts.get(g.id, {'host': 0, 'database': 0, 'middleware': 0})
            }
            for g in groups
        ]
    })


@assets_bp.route('/assets/groups', methods=['POST'])
def create_group():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name 不能为空'}), 400
    if AssetGroup.query.filter_by(name=name).first():
        return jsonify({'error': '分组名称已存在'}), 400
    g = AssetGroup(name=name, description=(data.get('description') or '').strip() or None)
    db.session.add(g)
    db.session.commit()
    return jsonify(g.to_dict()), 201


@assets_bp.route('/assets/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    g = AssetGroup.query.get_or_404(group_id)
    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name 不能为空'}), 400
        if AssetGroup.query.filter(AssetGroup.name == name, AssetGroup.id != g.id).first():
            return jsonify({'error': '分组名称已存在'}), 400
        g.name = name
    if 'description' in data:
        g.description = (data.get('description') or '').strip() or None
    db.session.commit()
    return jsonify(g.to_dict())


@assets_bp.route('/assets/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    g = AssetGroup.query.get_or_404(group_id)
    db.session.delete(g)
    db.session.commit()
    return jsonify({'message': 'Group deleted'})


@assets_bp.route('/assets/groups/<int:group_id>/members', methods=['GET'])
def list_group_members(group_id):
    g = AssetGroup.query.get_or_404(group_id)
    members = AssetGroupMember.query.filter_by(group_id=g.id).order_by(AssetGroupMember.created_at.desc()).all()
    items = []
    for m in members:
        obj = None
        if m.asset_type == AssetType.HOST:
            obj = Host.query.get(m.asset_id)
        elif m.asset_type == AssetType.DATABASE:
            obj = Database.query.get(m.asset_id)
        else:
            obj = Middleware.query.get(m.asset_id)
        if not obj:
            continue
        items.append({
            **m.to_dict(),
            'label': _asset_label(m.asset_type, obj)
        })
    return jsonify({'group': g.to_dict(), 'members': items})


@assets_bp.route('/assets/groups/<int:group_id>/members', methods=['POST'])
def update_group_members(group_id):
    g = AssetGroup.query.get_or_404(group_id)
    data = request.get_json() or {}
    add = data.get('add') or []
    remove = data.get('remove') or []

    added = 0
    removed = 0
    errors = []

    for item in add:
        try:
            a_type = _parse_asset_type(item.get('type'))
            a_id = int(item.get('id'))
            if not a_type:
                raise ValueError('Invalid type')
            exists = AssetGroupMember.query.filter_by(group_id=g.id, asset_type=a_type, asset_id=a_id).first()
            if exists:
                continue
            db.session.add(AssetGroupMember(group_id=g.id, asset_type=a_type, asset_id=a_id))
            added += 1
        except Exception as e:
            errors.append({'action': 'add', 'item': item, 'error': str(e)})

    for item in remove:
        try:
            a_type = _parse_asset_type(item.get('type'))
            a_id = int(item.get('id'))
            if not a_type:
                raise ValueError('Invalid type')
            m = AssetGroupMember.query.filter_by(group_id=g.id, asset_type=a_type, asset_id=a_id).first()
            if not m:
                continue
            db.session.delete(m)
            removed += 1
        except Exception as e:
            errors.append({'action': 'remove', 'item': item, 'error': str(e)})

    db.session.commit()
    return jsonify({'added': added, 'removed': removed, 'errors': errors})
