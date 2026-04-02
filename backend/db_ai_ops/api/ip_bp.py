from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import AssetType, IdcDict, IpAsset, IpStatus, IpVersion

ip_bp = Blueprint('ip_bp', __name__)


def _parse_status(v):
    if not v:
        return None
    try:
        return IpStatus(str(v).strip().lower())
    except ValueError:
        return None


def _parse_version(v):
    if not v:
        return None
    try:
        return IpVersion(str(v).strip().lower())
    except ValueError:
        return None


def _parse_asset_type(v):
    if not v:
        return None
    try:
        return AssetType(str(v).strip().lower())
    except ValueError:
        return None


@ip_bp.route('/ips', methods=['GET'])
def list_ips():
    q = (request.args.get('q') or '').strip().lower()
    status = _parse_status(request.args.get('status'))
    env = (request.args.get('env') or '').strip()
    idc_id = request.args.get('idc_id', type=int)
    system_id = request.args.get('system_id', type=int)

    query = IpAsset.query
    if status:
        query = query.filter_by(status=status)
    if env:
        query = query.filter_by(env=env)
    if idc_id:
        query = query.filter_by(idc_id=idc_id)
    if system_id:
        query = query.filter_by(business_system_id=system_id)

    items = query.order_by(IpAsset.created_at.desc()).all()
    out = []
    for ip in items:
        sys_name = ip.business_system.name if ip.business_system else ''
        text = f"{ip.ip} {ip.owner or ''} {ip.env or ''} {ip.remark or ''} {sys_name}"
        if q and q not in text.lower():
            continue
        out.append(ip.to_dict())
    return jsonify({'ips': out})


@ip_bp.route('/ips', methods=['POST'])
def create_ip():
    data = request.get_json() or {}
    ip = (data.get('ip') or '').strip()
    if not ip:
        return jsonify({'error': 'ip 不能为空'}), 400
    if IpAsset.query.filter_by(ip=ip).first():
        return jsonify({'error': 'IP已存在'}), 400

    version = _parse_version(data.get('version')) or IpVersion.IPV4
    status = _parse_status(data.get('status')) or IpStatus.FREE

    idc_id = int(data['idc_id']) if data.get('idc_id') else None
    if idc_id and not IdcDict.query.get(idc_id):
        return jsonify({'error': 'idc_id 不存在'}), 400

    a_type = _parse_asset_type(data.get('assigned_asset_type'))
    a_id = int(data['assigned_asset_id']) if data.get('assigned_asset_id') else None

    item = IpAsset(
        ip=ip,
        cidr=int(data['cidr']) if data.get('cidr') else None,
        version=version,
        status=status,
        business_system_id=int(data['business_system_id']) if data.get('business_system_id') else None,
        owner=(data.get('owner') or '').strip() or None,
        env=(data.get('env') or '').strip() or None,
        idc_id=idc_id,
        remark=(data.get('remark') or '').strip() or None,
        tags=data.get('tags') or [],
        assigned_asset_type=a_type,
        assigned_asset_id=a_id
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@ip_bp.route('/ips/<int:ip_id>', methods=['PUT'])
def update_ip(ip_id):
    item = IpAsset.query.get_or_404(ip_id)
    data = request.get_json() or {}

    for field in ['owner', 'env', 'remark']:
        if field in data:
            val = (data.get(field) or '').strip()
            setattr(item, field, val or None)

    if 'cidr' in data:
        item.cidr = int(data['cidr']) if data.get('cidr') else None

    if 'version' in data:
        v = _parse_version(data.get('version'))
        if not v:
            return jsonify({'error': 'Invalid version'}), 400
        item.version = v

    if 'status' in data:
        s = _parse_status(data.get('status'))
        if not s:
            return jsonify({'error': 'Invalid status'}), 400
        item.status = s

    if 'business_system_id' in data:
        item.business_system_id = int(data['business_system_id']) if data.get('business_system_id') else None

    if 'idc_id' in data:
        idc_id = int(data['idc_id']) if data.get('idc_id') else None
        if idc_id and not IdcDict.query.get(idc_id):
            return jsonify({'error': 'idc_id 不存在'}), 400
        item.idc_id = idc_id

    if 'tags' in data:
        item.tags = data.get('tags') or []

    if 'assigned_asset_type' in data or 'assigned_asset_id' in data:
        a_type = _parse_asset_type(data.get('assigned_asset_type'))
        a_id = int(data['assigned_asset_id']) if data.get('assigned_asset_id') else None
        item.assigned_asset_type = a_type
        item.assigned_asset_id = a_id
        if a_type and a_id:
            item.status = IpStatus.ALLOCATED
        elif not a_type and not a_id and item.status == IpStatus.ALLOCATED:
            item.status = IpStatus.FREE

    db.session.commit()
    return jsonify(item.to_dict())


@ip_bp.route('/ips/<int:ip_id>', methods=['DELETE'])
def delete_ip(ip_id):
    item = IpAsset.query.get_or_404(ip_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'IP deleted'})


@ip_bp.route('/ips/statuses', methods=['GET'])
def ip_statuses():
    return jsonify({
        'statuses': [{'value': e.value, 'label': e.value.upper()} for e in IpStatus],
        'versions': [{'value': e.value, 'label': e.value.upper()} for e in IpVersion]
    })
