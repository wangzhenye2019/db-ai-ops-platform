from flask import Blueprint, current_app, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Database, DatabaseType

database_bp = Blueprint('database_bp', __name__)


@database_bp.route('/databases', methods=['GET'])
def list_databases():
    databases = Database.query.order_by(Database.created_at.desc()).all()
    return jsonify({
        'databases': [db.to_dict() for db in databases]
    })


@database_bp.route('/databases', methods=['POST'])
def create_database():
    data = request.get_json() or {}

    required_fields = ['name', 'db_type', 'host', 'port', 'database', 'username']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    if not data.get('password') and not data.get('credential_id'):
        return jsonify({'error': 'password or credential_id is required'}), 400

    try:
        db_type = DatabaseType(data['db_type'])
    except ValueError:
        return jsonify({'error': f'Invalid database type. Must be one of: {[e.value for e in DatabaseType]}'}), 400

    database = Database(
        name=data['name'],
        db_type=db_type,
        host=data['host'],
        port=data['port'],
        database=data['database'],
        username=data['username'],
        password=data.get('password') or '',
        credential_id=int(data['credential_id']) if data.get('credential_id') else None,
        business_system_id=int(data['business_system_id']) if data.get('business_system_id') else None,
        owner=(data.get('owner') or '').strip() or None,
        env=(data.get('env') or '').strip() or None,
        version=(data.get('version') or '').strip() or None,
        remark=(data.get('remark') or '').strip() or None,
        enabled=data.get('enabled', True)
    )

    db.session.add(database)
    db.session.commit()

    return jsonify(database.to_dict()), 201


@database_bp.route('/databases/<int:database_id>', methods=['GET'])
def get_database(database_id):
    database = Database.query.get_or_404(database_id)
    return jsonify(database.to_dict())


@database_bp.route('/databases/<int:database_id>', methods=['PUT'])
def update_database(database_id):
    database = Database.query.get_or_404(database_id)
    data = request.get_json() or {}

    for field in ['name', 'host', 'port', 'database', 'username', 'password', 'enabled', 'owner', 'env', 'version', 'remark']:
        if field in data:
            val = data[field]
            if isinstance(val, str):
                val = val.strip()
            setattr(database, field, val or None)

    if 'business_system_id' in data:
        database.business_system_id = int(data['business_system_id']) if data.get('business_system_id') else None

    if 'credential_id' in data:
        database.credential_id = int(data['credential_id']) if data.get('credential_id') else None

    if 'db_type' in data:
        try:
            database.db_type = DatabaseType(data['db_type'])
        except ValueError:
            return jsonify({'error': 'Invalid database type'}), 400

    db.session.commit()
    return jsonify(database.to_dict())


@database_bp.route('/databases/<int:database_id>', methods=['DELETE'])
def delete_database(database_id):
    database = Database.query.get_or_404(database_id)
    db.session.delete(database)
    db.session.commit()

    return jsonify({'message': 'Database deleted'})


@database_bp.route('/databases/types', methods=['GET'])
def get_database_types():
    return jsonify({
        'types': [
            {'value': 'mysql', 'label': 'MySQL', 'default_port': 3306},
            {'value': 'postgresql', 'label': 'PostgreSQL', 'default_port': 5432},
            {'value': 'oracle', 'label': 'Oracle', 'default_port': 1521},
            {'value': 'mssql', 'label': 'SQL Server', 'default_port': 1433}
        ]
    })


@database_bp.route('/databases/<int:database_id>/test', methods=['POST'])
def test_connection(database_id):
    database = Database.query.get_or_404(database_id)

    try:
        password = database.password
        if (not password) and database.credential_id:
            from db_ai_ops.crypto import decrypt_text
            from db_ai_ops.models import Credential

            c = Credential.query.get(database.credential_id)
            if c:
                password = decrypt_text(c.secret_encrypted, current_app.config['SECRET_KEY'])

        if database.db_type == DatabaseType.MYSQL:
            try:
                import pymysql
            except ImportError:
                return jsonify({'status': 'failed', 'message': 'Missing driver: pymysql. Install backend/requirements-drivers.txt'}), 400
            conn = pymysql.connect(
                host=database.host,
                port=database.port,
                user=database.username,
                password=password,
                database=database.database
            )
            conn.close()
        elif database.db_type == DatabaseType.POSTGRESQL:
            try:
                import psycopg2
            except ImportError:
                return jsonify({'status': 'failed', 'message': 'Missing driver: psycopg2. Install backend/requirements-drivers.txt'}), 400
            conn = psycopg2.connect(
                host=database.host,
                port=database.port,
                user=database.username,
                password=password,
                database=database.database
            )
            conn.close()
        elif database.db_type == DatabaseType.ORACLE:
            try:
                import cx_Oracle
            except ImportError:
                return jsonify({'status': 'failed', 'message': 'Missing driver: cx_Oracle. Install backend/requirements-drivers.txt'}), 400
            dsn = cx_Oracle.makedsn(database.host, database.port, database.database)
            conn = cx_Oracle.connect(database.username, password, dsn)
            conn.close()
        elif database.db_type == DatabaseType.MSSQL:
            try:
                import pymssql
            except ImportError:
                return jsonify({'status': 'failed', 'message': 'Missing driver: pymssql. Install backend/requirements-drivers.txt'}), 400
            conn = pymssql.connect(
                server=database.host,
                port=database.port,
                user=database.username,
                password=password,
                database=database.database
            )
            conn.close()

        return jsonify({'status': 'success', 'message': 'Connection successful'})
    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 400
