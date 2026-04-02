import io
from contextlib import nullcontext

from flask import Blueprint, jsonify, request, send_file

from db_ai_ops.extensions import db
from db_ai_ops.imports import (
    build_csv_template,
    build_tsv_template,
    build_xlsx_template,
    normalize_headers,
    parse_bool,
    parse_json,
    parse_tags,
    read_csv_or_txt,
    read_xlsx,
    rows_to_dicts
)
from db_ai_ops.models import BusinessSystem, Database, DatabaseType, Host, HostOSType, IdcDict, IpAsset, IpStatus, IpVersion, Middleware, MiddlewareType

import_bp = Blueprint('import_bp', __name__)


RESOURCE_SPECS = {
    'databases': {
        'headers': ['name', 'db_type', 'host', 'port', 'database', 'username', 'password', 'business_system', 'owner', 'env', 'version', 'remark', 'enabled'],
        'example': ['db1', 'mysql', '127.0.0.1', 3306, 'test', 'root', 'password', 'order-center', '张三', 'prod', '8.0', '核心库', True],
        'mapping': {
            '名称': 'name',
            '类型': 'db_type',
            '主机': 'host',
            '端口': 'port',
            '数据库': 'database',
            '用户名': 'username',
            '密码': 'password',
            '业务系统': 'business_system',
            '负责人': 'owner',
            '环境': 'env',
            '版本': 'version',
            '备注': 'remark',
            '状态': 'enabled',
            'enabled': 'enabled'
        }
    },
    'hosts': {
        'headers': ['name', 'host', 'port', 'os_type', 'hostname', 'os_version', 'username', 'password', 'business_system', 'owner', 'env', 'idc', 'remark', 'tags', 'enabled'],
        'example': ['host1', '192.168.1.10', 22, 'linux', 'web-01', 'ubuntu22.04', 'root', 'password', 'order-center', '张三', 'prod', '北京-机房A', '核心节点', 'prod,web', True],
        'mapping': {
            '名称': 'name',
            'ip': 'host',
            'ip/域名': 'host',
            'ip/域名 ': 'host',
            'IP/域名': 'host',
            '主机': 'host',
            '端口': 'port',
            '类型': 'os_type',
            '主机名': 'hostname',
            'hostname': 'hostname',
            'OS版本': 'os_version',
            'os_version': 'os_version',
            '用户名': 'username',
            '密码': 'password',
            '业务系统': 'business_system',
            '负责人': 'owner',
            '环境': 'env',
            '机房': 'idc',
            '备注': 'remark',
            '状态': 'enabled',
            '标签': 'tags',
            'enabled': 'enabled'
        }
    },
    'middlewares': {
        'headers': ['name', 'mw_type', 'host', 'port', 'version', 'business_system', 'owner', 'env', 'remark', 'enabled', 'meta'],
        'example': ['redis-1', 'redis', '192.168.1.20', 6379, '7.2', 'order-center', '张三', 'prod', '缓存', True, '{"cluster":"c1"}'],
        'mapping': {
            '名称': 'name',
            '类型': 'mw_type',
            '主机': 'host',
            '端口': 'port',
            '版本': 'version',
            '业务系统': 'business_system',
            '负责人': 'owner',
            '环境': 'env',
            '备注': 'remark',
            '状态': 'enabled',
            '元数据': 'meta',
            'enabled': 'enabled'
        }
    }
    ,
    'ips': {
        'headers': ['ip', 'cidr', 'version', 'status', 'business_system', 'owner', 'env', 'idc', 'remark', 'tags'],
        'example': ['10.0.0.10', 24, 'ipv4', 'free', 'order-center', '张三', 'prod', '北京-机房A', '网段预留', 'prod,web'],
        'mapping': {
            'IP': 'ip',
            'ip': 'ip',
            '掩码': 'cidr',
            'cidr': 'cidr',
            '版本': 'version',
            'version': 'version',
            '状态': 'status',
            'status': 'status',
            '业务系统': 'business_system',
            '负责人': 'owner',
            '环境': 'env',
            '机房': 'idc',
            '备注': 'remark',
            '标签': 'tags'
        }
    }
}


def _read_upload(file_storage):
    filename = (file_storage.filename or '').lower()
    data = file_storage.read()
    if filename.endswith('.xlsx'):
        return read_xlsx(data)
    if filename.endswith('.csv') or filename.endswith('.txt'):
        return read_csv_or_txt(data)
    return read_csv_or_txt(data)


@import_bp.route('/import/templates/<resource>', methods=['GET'])
def download_template(resource):
    fmt = (request.args.get('format') or 'csv').lower()
    if resource not in RESOURCE_SPECS:
        return jsonify({'error': 'Invalid resource'}), 400
    spec = RESOURCE_SPECS[resource]
    headers = spec['headers']
    example = spec['example']

    if fmt == 'xlsx':
        content = build_xlsx_template(headers, example)
        return send_file(
            io.BytesIO(content),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{resource}_template.xlsx'
        )
    if fmt == 'txt':
        content = build_tsv_template(headers, example)
        return send_file(
            io.BytesIO(content),
            mimetype='text/plain; charset=utf-8',
            as_attachment=True,
            download_name=f'{resource}_template.txt'
        )
    content = build_csv_template(headers, example)
    return send_file(
        io.BytesIO(content),
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=f'{resource}_template.csv'
    )


@import_bp.route('/import/<resource>', methods=['POST'])
def import_resource(resource):
    if resource not in RESOURCE_SPECS:
        return jsonify({'error': 'Invalid resource'}), 400
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'file is required'}), 400

    dry_run = request.args.get('dry_run', '0') == '1'
    mode = (request.args.get('mode') or 'insert').lower()
    if mode not in {'insert', 'upsert'}:
        return jsonify({'error': 'Invalid mode'}), 400
    spec = RESOURCE_SPECS[resource]

    headers, rows = _read_upload(file)
    if not headers:
        return jsonify({'error': 'Empty file'}), 400

    headers = normalize_headers(headers, spec['mapping'])
    data_rows = rows_to_dicts(headers, rows)

    def _mask_preview(item):
        masked = dict(item)
        if 'password' in masked and masked.get('password'):
            masked['password'] = '******'
        return masked

    total = len(data_rows)
    errors = []
    preview = []
    created_count = 0
    updated_count = 0
    skipped_count = 0
    system_cache = {}

    def _resolve_system_id(raw_value, allow_create):
        key = str(raw_value or '').strip()
        if not key:
            return None, None
        if key in system_cache:
            return system_cache[key], key
        s = BusinessSystem.query.filter((BusinessSystem.name == key) | (BusinessSystem.code == key)).first()
        if not s and allow_create:
            s = BusinessSystem(name=key, enabled=True)
            db.session.add(s)
            db.session.flush()
        system_cache[key] = s.id if s else None
        return system_cache[key], key

    for line_no, row in enumerate(data_rows, start=2):
        try:
            ctx = db.session.begin_nested() if not dry_run else nullcontext()
            with ctx:
                if resource == 'hosts':
                    name = str(row.get('name') or '').strip()
                    host = str(row.get('host') or '').strip()
                    if not name or not host:
                        raise ValueError('name/host 不能为空')
                    port = int(row.get('port') or 22)
                    os_type_raw = str(row.get('os_type') or 'linux').strip().lower()
                    os_type = HostOSType(os_type_raw)
                    username = str(row.get('username') or '').strip() or None
                    password = str(row.get('password') or '').strip() or None
                    enabled_raw = row.get('enabled')
                    enabled = parse_bool(enabled_raw, None)
                    tags_raw = row.get('tags')
                    tags = parse_tags(tags_raw)
                    hostname = str(row.get('hostname') or '').strip() or None
                    os_version = str(row.get('os_version') or '').strip() or None
                    owner = str(row.get('owner') or '').strip() or None
                    env = str(row.get('env') or '').strip() or None
                    idc = str(row.get('idc') or '').strip() or None
                    remark = str(row.get('remark') or '').strip() or None
                    bs_id, bs_key = _resolve_system_id(row.get('business_system'), allow_create=not dry_run)

                    existing = Host.query.filter_by(host=host, port=port).first()
                    action = None
                    if existing:
                        if mode == 'insert':
                            raise ValueError('记录已存在（host+port）')
                        action = 'update'
                        if not dry_run:
                            existing.name = name
                            existing.os_type = os_type
                            if username is not None:
                                existing.username = username
                            if password:
                                existing.password = password
                            if enabled is not None:
                                existing.enabled = enabled
                            if str(tags_raw or '').strip() != '':
                                existing.tags = tags
                            if hostname is not None:
                                existing.hostname = hostname
                            if os_version is not None:
                                existing.os_version = os_version
                            if owner is not None:
                                existing.owner = owner
                            if env is not None:
                                existing.env = env
                            if idc is not None:
                                existing.idc = idc
                            if remark is not None:
                                existing.remark = remark
                            if bs_id is not None:
                                existing.business_system_id = bs_id
                    else:
                        action = 'create'
                        if not dry_run:
                            h = Host(
                                name=name,
                                host=host,
                                port=port,
                                os_type=os_type,
                                hostname=hostname,
                                os_version=os_version,
                                username=username,
                                password=password,
                                business_system_id=bs_id,
                                owner=owner,
                                env=env,
                                idc=idc,
                                remark=remark,
                                enabled=enabled if enabled is not None else True,
                                tags=tags
                            )
                            db.session.add(h)

                    if action == 'create':
                        created_count += 1
                    elif action == 'update':
                        updated_count += 1

                    if dry_run and len(preview) < 20:
                        preview.append(_mask_preview({
                            'row': line_no,
                            'action': action,
                            'name': name,
                            'host': host,
                            'port': port,
                            'os_type': os_type.value,
                            'business_system': bs_key,
                            'owner': owner,
                            'env': env,
                            'username': username,
                            'password': password,
                            'enabled': enabled if enabled is not None else '',
                            'tags': tags
                        }))

                elif resource == 'databases':
                    name = str(row.get('name') or '').strip()
                    db_type_raw = str(row.get('db_type') or '').strip().lower()
                    host = str(row.get('host') or '').strip()
                    port = row.get('port')
                    database = str(row.get('database') or '').strip()
                    username = str(row.get('username') or '').strip()
                    password = str(row.get('password') or '').strip()
                    enabled_raw = row.get('enabled')
                    enabled = parse_bool(enabled_raw, None)
                    owner = str(row.get('owner') or '').strip() or None
                    env = str(row.get('env') or '').strip() or None
                    version = str(row.get('version') or '').strip() or None
                    remark = str(row.get('remark') or '').strip() or None
                    bs_id, bs_key = _resolve_system_id(row.get('business_system'), allow_create=not dry_run)

                    if not name or not db_type_raw or not host or port is None or not database or not username:
                        raise ValueError('name/db_type/host/port/database/username 不能为空')
                    db_type = DatabaseType(db_type_raw)
                    port = int(port)

                    existing = Database.query.filter_by(db_type=db_type, host=host, port=port, database=database).first()
                    action = None
                    if existing:
                        if mode == 'insert':
                            raise ValueError('记录已存在（db_type+host+port+database）')
                        action = 'update'
                        if not dry_run:
                            existing.name = name
                            existing.username = username
                            if password:
                                existing.password = password
                            if enabled is not None:
                                existing.enabled = enabled
                            if owner is not None:
                                existing.owner = owner
                            if env is not None:
                                existing.env = env
                            if version is not None:
                                existing.version = version
                            if remark is not None:
                                existing.remark = remark
                            if bs_id is not None:
                                existing.business_system_id = bs_id
                    else:
                        action = 'create'
                        if not dry_run:
                            d = Database(
                                name=name,
                                db_type=db_type,
                                host=host,
                                port=port,
                                database=database,
                                username=username,
                                password=password,
                                business_system_id=bs_id,
                                owner=owner,
                                env=env,
                                version=version,
                                remark=remark,
                                enabled=enabled if enabled is not None else True
                            )
                            db.session.add(d)

                    if action == 'create':
                        created_count += 1
                    elif action == 'update':
                        updated_count += 1

                    if dry_run and len(preview) < 20:
                        preview.append(_mask_preview({
                            'row': line_no,
                            'action': action,
                            'name': name,
                            'db_type': db_type.value,
                            'host': host,
                            'port': port,
                            'database': database,
                            'username': username,
                            'password': password,
                            'business_system': bs_key,
                            'owner': owner,
                            'env': env,
                            'enabled': enabled if enabled is not None else ''
                        }))

                elif resource == 'ips':
                    ip = str(row.get('ip') or '').strip()
                    cidr = row.get('cidr')
                    version_raw = str(row.get('version') or 'ipv4').strip().lower()
                    status_raw = str(row.get('status') or 'free').strip().lower()
                    owner = str(row.get('owner') or '').strip() or None
                    env = str(row.get('env') or '').strip() or None
                    remark = str(row.get('remark') or '').strip() or None
                    tags_raw = row.get('tags')
                    tags = parse_tags(tags_raw)
                    idc_name = str(row.get('idc') or '').strip()
                    bs_id, bs_key = _resolve_system_id(row.get('business_system'), allow_create=not dry_run)

                    if not ip:
                        raise ValueError('ip 不能为空')

                    try:
                        version = IpVersion(version_raw)
                    except ValueError:
                        raise ValueError('version 无效')

                    try:
                        status = IpStatus(status_raw)
                    except ValueError:
                        raise ValueError('status 无效')

                    idc_id = None
                    if idc_name:
                        idc = IdcDict.query.filter_by(name=idc_name).first()
                        if not idc and not dry_run:
                            idc = IdcDict(name=idc_name)
                            db.session.add(idc)
                            db.session.flush()
                        idc_id = idc.id if idc else None

                    existing = IpAsset.query.filter_by(ip=ip).first()
                    action = None
                    if existing:
                        if mode == 'insert':
                            raise ValueError('记录已存在（ip）')
                        action = 'update'
                        if not dry_run:
                            existing.cidr = int(cidr) if cidr else None
                            existing.version = version
                            existing.status = status
                            existing.business_system_id = bs_id
                            existing.owner = owner
                            existing.env = env
                            existing.idc_id = idc_id
                            existing.remark = remark
                            if str(tags_raw or '').strip() != '':
                                existing.tags = tags
                    else:
                        action = 'create'
                        if not dry_run:
                            x = IpAsset(
                                ip=ip,
                                cidr=int(cidr) if cidr else None,
                                version=version,
                                status=status,
                                business_system_id=bs_id,
                                owner=owner,
                                env=env,
                                idc_id=idc_id,
                                remark=remark,
                                tags=tags
                            )
                            db.session.add(x)

                    if action == 'create':
                        created_count += 1
                    elif action == 'update':
                        updated_count += 1

                    if dry_run and len(preview) < 20:
                        preview.append({
                            'row': line_no,
                            'action': action,
                            'ip': ip,
                            'cidr': int(cidr) if cidr else None,
                            'version': version.value,
                            'status': status.value,
                            'business_system': bs_key,
                            'owner': owner,
                            'env': env,
                            'idc': idc_name,
                            'remark': remark,
                            'tags': tags
                        })

                else:
                    name = str(row.get('name') or '').strip()
                    mw_type_raw = str(row.get('mw_type') or '').strip().lower()
                    host = str(row.get('host') or '').strip()
                    port = row.get('port')
                    version = str(row.get('version') or '').strip() or None
                    enabled_raw = row.get('enabled')
                    enabled = parse_bool(enabled_raw, None)
                    owner = str(row.get('owner') or '').strip() or None
                    env = str(row.get('env') or '').strip() or None
                    remark = str(row.get('remark') or '').strip() or None
                    meta_raw = row.get('meta')
                    meta = parse_json(meta_raw, {})
                    bs_id, bs_key = _resolve_system_id(row.get('business_system'), allow_create=not dry_run)

                    if not name or not mw_type_raw or not host or port is None:
                        raise ValueError('name/mw_type/host/port 不能为空')
                    mw_type = MiddlewareType(mw_type_raw)
                    port = int(port)

                    existing = Middleware.query.filter_by(mw_type=mw_type, host=host, port=port).first()
                    action = None
                    if existing:
                        if mode == 'insert':
                            raise ValueError('记录已存在（mw_type+host+port）')
                        action = 'update'
                        if not dry_run:
                            existing.name = name
                            existing.version = version
                            if enabled is not None:
                                existing.enabled = enabled
                            if str(meta_raw or '').strip() != '':
                                existing.meta = meta
                            if owner is not None:
                                existing.owner = owner
                            if env is not None:
                                existing.env = env
                            if remark is not None:
                                existing.remark = remark
                            if bs_id is not None:
                                existing.business_system_id = bs_id
                    else:
                        action = 'create'
                        if not dry_run:
                            m = Middleware(
                                name=name,
                                mw_type=mw_type,
                                host=host,
                                port=port,
                                version=version,
                                business_system_id=bs_id,
                                owner=owner,
                                env=env,
                                remark=remark,
                                enabled=enabled if enabled is not None else True,
                                meta=meta
                            )
                            db.session.add(m)

                    if action == 'create':
                        created_count += 1
                    elif action == 'update':
                        updated_count += 1

                    if dry_run and len(preview) < 20:
                        preview.append({
                            'row': line_no,
                            'action': action,
                            'name': name,
                            'mw_type': mw_type.value,
                            'host': host,
                            'port': port,
                            'version': version,
                            'business_system': bs_key,
                            'owner': owner,
                            'env': env,
                            'enabled': enabled if enabled is not None else '',
                            'meta': meta
                        })

        except Exception as e:
            errors.append({'row': line_no, 'error': str(e)})
            skipped_count += 1

    if dry_run:
        return jsonify({
            'resource': resource,
            'dry_run': True,
            'mode': mode,
            'total': total,
            'created': created_count,
            'updated': updated_count,
            'failed': len(errors),
            'errors': errors,
            'preview': preview
        })

    db.session.commit()

    return jsonify({
        'resource': resource,
        'dry_run': False,
        'mode': mode,
        'total': total,
        'created': created_count,
        'updated': updated_count,
        'success': created_count + updated_count,
        'failed': len(errors),
        'errors': errors
    })
