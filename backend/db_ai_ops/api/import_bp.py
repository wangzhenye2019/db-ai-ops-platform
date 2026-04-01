import io

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
from db_ai_ops.models import Database, DatabaseType, Host, HostOSType, Middleware, MiddlewareType

import_bp = Blueprint('import_bp', __name__)


RESOURCE_SPECS = {
    'databases': {
        'headers': ['name', 'db_type', 'host', 'port', 'database', 'username', 'password', 'enabled'],
        'example': ['db1', 'mysql', '127.0.0.1', 3306, 'test', 'root', 'password', True],
        'mapping': {
            '名称': 'name',
            '类型': 'db_type',
            '主机': 'host',
            '端口': 'port',
            '数据库': 'database',
            '用户名': 'username',
            '密码': 'password',
            '状态': 'enabled',
            'enabled': 'enabled'
        }
    },
    'hosts': {
        'headers': ['name', 'host', 'port', 'os_type', 'username', 'password', 'enabled', 'tags'],
        'example': ['host1', '192.168.1.10', 22, 'linux', 'root', 'password', True, 'prod,db'],
        'mapping': {
            '名称': 'name',
            'ip': 'host',
            'ip/域名': 'host',
            'ip/域名 ': 'host',
            'IP/域名': 'host',
            '主机': 'host',
            '端口': 'port',
            '类型': 'os_type',
            '用户名': 'username',
            '密码': 'password',
            '状态': 'enabled',
            '标签': 'tags',
            'enabled': 'enabled'
        }
    },
    'middlewares': {
        'headers': ['name', 'mw_type', 'host', 'port', 'version', 'enabled', 'meta'],
        'example': ['redis-1', 'redis', '192.168.1.20', 6379, '7.2', True, '{"cluster":"c1"}'],
        'mapping': {
            '名称': 'name',
            '类型': 'mw_type',
            '主机': 'host',
            '端口': 'port',
            '版本': 'version',
            '状态': 'enabled',
            '元数据': 'meta',
            'enabled': 'enabled'
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
    spec = RESOURCE_SPECS[resource]

    headers, rows = _read_upload(file)
    if not headers:
        return jsonify({'error': 'Empty file'}), 400

    headers = normalize_headers(headers, spec['mapping'])
    data_rows = rows_to_dicts(headers, rows)

    total = len(data_rows)
    success = 0
    failed = 0
    errors = []

    created = []

    for idx, row in enumerate(data_rows, start=2):
        try:
            if resource == 'hosts':
                name = str(row.get('name') or '').strip()
                host = str(row.get('host') or '').strip()
                if not name or not host:
                    raise ValueError('name/host 不能为空')
                port = int(row.get('port') or 22)
                os_type_raw = str(row.get('os_type') or 'linux').strip().lower()
                os_type = HostOSType(os_type_raw)
                h = Host(
                    name=name,
                    host=host,
                    port=port,
                    os_type=os_type,
                    username=str(row.get('username') or '').strip() or None,
                    password=str(row.get('password') or '').strip() or None,
                    enabled=parse_bool(row.get('enabled'), True),
                    tags=parse_tags(row.get('tags'))
                )
                created.append(h)

            elif resource == 'databases':
                name = str(row.get('name') or '').strip()
                db_type_raw = str(row.get('db_type') or '').strip().lower()
                host = str(row.get('host') or '').strip()
                port = row.get('port')
                database = str(row.get('database') or '').strip()
                username = str(row.get('username') or '').strip()
                password = str(row.get('password') or '').strip()
                if not name or not db_type_raw or not host or port is None or not database or not username:
                    raise ValueError('name/db_type/host/port/database/username 不能为空')
                db_type = DatabaseType(db_type_raw)
                d = Database(
                    name=name,
                    db_type=db_type,
                    host=host,
                    port=int(port),
                    database=database,
                    username=username,
                    password=password,
                    enabled=parse_bool(row.get('enabled'), True)
                )
                created.append(d)

            else:
                name = str(row.get('name') or '').strip()
                mw_type_raw = str(row.get('mw_type') or '').strip().lower()
                host = str(row.get('host') or '').strip()
                port = row.get('port')
                if not name or not mw_type_raw or not host or port is None:
                    raise ValueError('name/mw_type/host/port 不能为空')
                mw_type = MiddlewareType(mw_type_raw)
                m = Middleware(
                    name=name,
                    mw_type=mw_type,
                    host=host,
                    port=int(port),
                    version=str(row.get('version') or '').strip() or None,
                    enabled=parse_bool(row.get('enabled'), True),
                    meta=parse_json(row.get('meta'), {})
                )
                created.append(m)

            success += 1
        except Exception as e:
            failed += 1
            errors.append({'row': idx, 'error': str(e)})

    if dry_run:
        return jsonify({
            'resource': resource,
            'dry_run': True,
            'total': total,
            'success': success,
            'failed': failed,
            'errors': errors
        })

    inserted = 0
    for obj in created:
        try:
            with db.session.begin_nested():
                db.session.add(obj)
            inserted += 1
        except Exception as e:
            errors.append({'row': None, 'error': str(e)})

    db.session.commit()

    return jsonify({
        'resource': resource,
        'dry_run': False,
        'total': total,
        'success': inserted,
        'failed': total - inserted,
        'errors': errors
    })
