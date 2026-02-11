from flask import Blueprint, jsonify, request
from app import db
from app.models import Database, DatabaseType

database_bp = Blueprint('database_bp', __name__)


@database_bp.route('/databases', methods=['GET'])
def list_databases():
    """List all databases"""
    databases = Database.query.order_by(Database.created_at.desc()).all()
    return jsonify({
        'databases': [db.to_dict() for db in databases]
    })


@database_bp.route('/databases', methods=['POST'])
def create_database():
    """Add a new database"""
    data = request.get_json()

    required_fields = ['name', 'db_type', 'host', 'port', 'database', 'username', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    # Validate database type
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
        password=data['password'],
        enabled=data.get('enabled', True)
    )

    db.session.add(database)
    db.session.commit()

    return jsonify(database.to_dict()), 201


@database_bp.route('/databases/<int:database_id>', methods=['GET'])
def get_database(database_id):
    """Get database details"""
    database = Database.query.get_or_404(database_id)
    return jsonify(database.to_dict())


@database_bp.route('/databases/<int:database_id>', methods=['PUT'])
def update_database(database_id):
    """Update database configuration"""
    database = Database.query.get_or_404(database_id)
    data = request.get_json()

    # Update fields
    for field in ['name', 'host', 'port', 'database', 'username', 'password', 'enabled']:
        if field in data:
            setattr(database, field, data[field])

    # Update database type if provided
    if 'db_type' in data:
        try:
            database.db_type = DatabaseType(data['db_type'])
        except ValueError:
            return jsonify({'error': 'Invalid database type'}), 400

    db.session.commit()
    return jsonify(database.to_dict())


@database_bp.route('/databases/<int:database_id>', methods=['DELETE'])
def delete_database(database_id):
    """Delete database"""
    database = Database.query.get_or_404(database_id)
    db.session.delete(database)
    db.session.commit()

    return jsonify({'message': 'Database deleted'})


@database_bp.route('/databases/types', methods=['GET'])
def get_database_types():
    """Get supported database types"""
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
    """Test database connection"""
    database = Database.query.get_or_404(database_id)

    try:
        if database.db_type == DatabaseType.MYSQL:
            import pymysql
            conn = pymysql.connect(
                host=database.host,
                port=database.port,
                user=database.username,
                password=database.password,
                database=database.database
            )
            conn.close()
        elif database.db_type == DatabaseType.POSTGRESQL:
            import psycopg2
            conn = psycopg2.connect(
                host=database.host,
                port=database.port,
                user=database.username,
                password=database.password,
                database=database.database
            )
            conn.close()
        elif database.db_type == DatabaseType.ORACLE:
            import cx_Oracle
            dsn = cx_Oracle.makedsn(database.host, database.port, database.database)
            conn = cx_Oracle.connect(database.username, database.password, dsn)
            conn.close()
        elif database.db_type == DatabaseType.MSSQL:
            import pymssql
            conn = pymssql.connect(
                server=database.host,
                port=database.port,
                user=database.username,
                password=database.password,
                database=database.database
            )
            conn.close()

        return jsonify({'status': 'success', 'message': 'Connection successful'})
    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 400
