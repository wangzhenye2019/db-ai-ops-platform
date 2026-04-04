from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Permission, Role, User

rbac_bp = Blueprint('rbac_bp', __name__)


# ==================== Permissions ====================

@rbac_bp.route('/permissions', methods=['GET'])
def list_permissions():
    permissions = Permission.query.all()
    return jsonify({
        'permissions': [p.to_dict() for p in permissions]
    })


@rbac_bp.route('/permissions', methods=['POST'])
def create_permission():
    data = request.get_json()
    name = data.get('name')
    code = data.get('code')
    category = data.get('category')
    description = data.get('description')

    if not name or not code:
        return jsonify({'error': 'name and code are required'}), 400

    if Permission.query.filter_by(code=code).first():
        return jsonify({'error': 'Permission code already exists'}), 400

    perm = Permission(name=name, code=code, category=category, description=description)
    db.session.add(perm)
    db.session.commit()

    return jsonify(perm.to_dict()), 201


@rbac_bp.route('/permissions/<int:perm_id>', methods=['DELETE'])
def delete_permission(perm_id):
    perm = Permission.query.get_or_404(perm_id)
    db.session.delete(perm)
    db.session.commit()
    return jsonify({'message': 'Permission deleted'})


# ==================== Roles ====================

@rbac_bp.route('/roles', methods=['GET'])
def list_roles():
    roles = Role.query.all()
    return jsonify({
        'roles': [r.to_dict() for r in roles]
    })


@rbac_bp.route('/roles', methods=['POST'])
def create_role():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    permission_ids = data.get('permission_ids', [])

    if not name:
        return jsonify({'error': 'name is required'}), 400

    if Role.query.filter_by(name=name).first():
        return jsonify({'error': 'Role name already exists'}), 400

    permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
    role = Role(name=name, description=description, permissions=permissions)
    db.session.add(role)
    db.session.commit()

    return jsonify(role.to_dict()), 201


@rbac_bp.route('/roles/<int:role_id>', methods=['GET'])
def get_role(role_id):
    role = Role.query.get_or_404(role_id)
    return jsonify(role.to_dict())


@rbac_bp.route('/roles/<int:role_id>', methods=['PUT'])
def update_role(role_id):
    role = Role.query.get_or_404(role_id)
    data = request.get_json()

    if data.get('name'):
        role.name = data['name']
    if data.get('description') is not None:
        role.description = data['description']
    if 'permission_ids' in data:
        permissions = Permission.query.filter(Permission.id.in_(data['permission_ids'])).all()
        role.permissions = permissions

    db.session.commit()
    return jsonify(role.to_dict())


@rbac_bp.route('/roles/<int:role_id>', methods=['DELETE'])
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    db.session.delete(role)
    db.session.commit()
    return jsonify({'message': 'Role deleted'})


# ==================== Users ====================

@rbac_bp.route('/users', methods=['GET'])
def list_users():
    users = User.query.all()
    return jsonify({
        'users': [{
            'id': u.id,
            'username': u.username,
            'enabled': u.enabled,
            'roles': [r.to_dict() for r in u.roles],
            'created_at': u.created_at.isoformat() if u.created_at else None
        } for u in users]
    })


@rbac_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role_ids = data.get('role_ids', [])

    if not username or not password:
        return jsonify({'error': 'username and password are required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    roles = Role.query.filter(Role.id.in_(role_ids)).all()
    user = User(username=username, enabled=True)
    user.set_password(password)
    user.roles = roles
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'enabled': user.enabled,
        'roles': [r.to_dict() for r in user.roles]
    }), 201


@rbac_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'enabled': user.enabled,
        'roles': [r.to_dict() for r in user.roles],
        'permissions': user.get_all_permissions(),
        'created_at': user.created_at.isoformat() if user.created_at else None
    })


@rbac_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if data.get('username'):
        user.username = data['username']
    if data.get('enabled') is not None:
        user.enabled = data['enabled']
    if data.get('password'):
        user.set_password(data['password'])
    if 'role_ids' in data:
        roles = Role.query.filter(Role.id.in_(data['role_ids'])).all()
        user.roles = roles

    db.session.commit()
    return jsonify({
        'id': user.id,
        'username': user.username,
        'enabled': user.enabled,
        'roles': [r.to_dict() for r in user.roles]
    })


@rbac_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'})


# ==================== Init Default Data ====================

@rbac_bp.route('/init', methods=['POST'])
def init_rbac():
    """初始化默认权限和角色"""
    # 默认权限
    default_permissions = [
        # 系统
        {'name': '用户管理', 'code': 'system:user', 'category': 'system', 'description': '用户管理'},
        {'name': '角色管理', 'code': 'system:role', 'category': 'system', 'description': '角色管理'},
        {'name': '权限管理', 'code': 'system:permission', 'category': 'system', 'description': '权限管理'},
        # 资产
        {'name': '主机管理', 'code': 'asset:host', 'category': 'asset', 'description': '主机管理'},
        {'name': '数据库管理', 'code': 'asset:database', 'category': 'asset', 'description': '数据库管理'},
        {'name': '中间件管理', 'code': 'asset:middleware', 'category': 'asset', 'description': '中间件管理'},
        # 备份
        {'name': '备份管理', 'code': 'backup:manage', 'category': 'backup', 'description': '备份管理'},
        {'name': '备份执行', 'code': 'backup:execute', 'category': 'backup', 'description': '执行备份'},
        {'name': '备份恢复', 'code': 'backup:restore', 'category': 'backup', 'description': '恢复备份'},
        # 监控
        {'name': '告警管理', 'code': 'monitor:alert', 'category': 'monitor', 'description': '告警管理'},
        {'name': '告警通知', 'code': 'monitor:notify', 'category': 'monitor', 'description': '告警通知配置'},
        # SQL审核
        {'name': 'SQL工单', 'code': 'sql:order', 'category': 'sql', 'description': 'SQL工单管理'},
        {'name': 'SQL审核', 'code': 'sql:audit', 'category': 'sql', 'description': 'SQL审核'},
        {'name': 'SQL执行', 'code': 'sql:execute', 'category': 'sql', 'description': 'SQL执行'},
    ]

    created_perms = []
    for p in default_permissions:
        if not Permission.query.filter_by(code=p['code']).first():
            perm = Permission(**p)
            db.session.add(perm)
            created_perms.append(p['code'])

    # 默认角色
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='管理员')
        admin_role.permissions = Permission.query.all()
        db.session.add(admin_role)

    operator_role = Role.query.filter_by(name='operator').first()
    if not operator_role:
        operator_role = Role(name='operator', description='运维人员')
        operator_role.permissions = Permission.query.filter(
            Permission.code.in_(['asset:host', 'asset:database', 'asset:middleware',
                               'backup:manage', 'backup:execute', 'backup:restore',
                               'monitor:alert', 'monitor:notify'])
        ).all()
        db.session.add(operator_role)

    developer_role = Role.query.filter_by(name='developer').first()
    if not developer_role:
        developer_role = Role(name='developer', description='开发人员')
        developer_role.permissions = Permission.query.filter(
            Permission.code.in_(['sql:order', 'sql:execute'])
        ).all()
        db.session.add(developer_role)

    db.session.commit()

    return jsonify({
        'message': 'RBAC initialized',
        'permissions_created': created_perms
    })
