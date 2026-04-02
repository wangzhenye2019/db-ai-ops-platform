from flask import Blueprint, jsonify, request, g

from db_ai_ops.extensions import db
from db_ai_ops.models import IdcDict, TagCategory, TagDict

dict_bp = Blueprint('dict_bp', __name__)


def _is_admin():
    roles = getattr(g, 'current_roles', []) or []
    return 'admin' in roles


@dict_bp.route('/dict/tags', methods=['GET'])
def list_tags():
    category = (request.args.get('category') or '').strip().lower()
    q = (request.args.get('q') or '').strip().lower()

    query = TagDict.query
    if category:
        try:
            query = query.filter_by(category=TagCategory(category))
        except ValueError:
            return jsonify({'error': 'Invalid category'}), 400

    tags = query.order_by(TagDict.created_at.desc()).all()
    items = []
    for t in tags:
        if q and q not in t.name.lower():
            continue
        items.append(t.to_dict())
    return jsonify({'tags': items})


@dict_bp.route('/dict/tags', methods=['POST'])
def create_tag():
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name 不能为空'}), 400
    if TagDict.query.filter_by(name=name).first():
        return jsonify({'error': '标签已存在'}), 400
    category_raw = (data.get('category') or 'asset').strip().lower()
    try:
        category = TagCategory(category_raw)
    except ValueError:
        return jsonify({'error': 'Invalid category'}), 400
    t = TagDict(name=name, category=category)
    db.session.add(t)
    db.session.commit()
    return jsonify(t.to_dict()), 201


@dict_bp.route('/dict/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    t = TagDict.query.get_or_404(tag_id)
    db.session.delete(t)
    db.session.commit()
    return jsonify({'message': 'Tag deleted'})


@dict_bp.route('/dict/idcs', methods=['GET'])
def list_idcs():
    q = (request.args.get('q') or '').strip().lower()
    items = IdcDict.query.order_by(IdcDict.created_at.desc()).all()
    out = []
    for i in items:
        text = f"{i.region or ''} {i.name}"
        if q and q not in text.lower():
            continue
        out.append(i.to_dict())
    return jsonify({'idcs': out})


@dict_bp.route('/dict/idcs', methods=['POST'])
def create_idc():
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name 不能为空'}), 400
    if IdcDict.query.filter_by(name=name).first():
        return jsonify({'error': '机房已存在'}), 400
    i = IdcDict(
        name=name,
        region=(data.get('region') or '').strip() or None,
        remark=(data.get('remark') or '').strip() or None
    )
    db.session.add(i)
    db.session.commit()
    return jsonify(i.to_dict()), 201


@dict_bp.route('/dict/idcs/<int:idc_id>', methods=['PUT'])
def update_idc(idc_id):
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    i = IdcDict.query.get_or_404(idc_id)
    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name 不能为空'}), 400
        if IdcDict.query.filter(IdcDict.name == name, IdcDict.id != i.id).first():
            return jsonify({'error': '机房已存在'}), 400
        i.name = name
    if 'region' in data:
        i.region = (data.get('region') or '').strip() or None
    if 'remark' in data:
        i.remark = (data.get('remark') or '').strip() or None
    db.session.commit()
    return jsonify(i.to_dict())


@dict_bp.route('/dict/idcs/<int:idc_id>', methods=['DELETE'])
def delete_idc(idc_id):
    if not _is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    i = IdcDict.query.get_or_404(idc_id)
    db.session.delete(i)
    db.session.commit()
    return jsonify({'message': 'Idc deleted'})

