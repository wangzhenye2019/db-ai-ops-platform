from flask import Blueprint, jsonify, request, g

from db_ai_ops.extensions import db
from db_ai_ops.models import Role, User

users_bp = Blueprint('users_bp', __name__)


def _require_admin():
    roles = getattr(g, 'current_roles', []) or []
    if 'admin' not in roles:
        return jsonify({'error': 'Forbidden'}), 403
    return None


@users_bp.route('/auth/users', methods=['GET'])
def list_users():
    deny = _require_admin()
    if deny:
        return deny
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [u.to_dict() for u in users]})


@users_bp.route('/auth/users', methods=['POST'])
def create_user():
    deny = _require_admin()
    if deny:
        return deny
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    roles = data.get('roles') or []

    if not username or not password:
        return jsonify({'error': 'username/password 不能为空'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 400

    u = User(username=username, enabled=bool(data.get('enabled', True)), password_hash='x')
    u.set_password(password)

    if roles:
        role_objs = Role.query.filter(Role.name.in_(roles)).all()
        u.roles = role_objs

    db.session.add(u)
    db.session.commit()
    return jsonify(u.to_dict()), 201


@users_bp.route('/auth/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    deny = _require_admin()
    if deny:
        return deny

    u = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    if 'enabled' in data:
        u.enabled = bool(data['enabled'])

    if 'password' in data and data['password']:
        u.set_password(data['password'])

    if 'roles' in data:
        roles = data.get('roles') or []
        role_objs = Role.query.filter(Role.name.in_(roles)).all()
        u.roles = role_objs

    db.session.commit()
    return jsonify(u.to_dict())


@users_bp.route('/auth/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    deny = _require_admin()
    if deny:
        return deny

    u = User.query.get_or_404(user_id)
    if u.id == getattr(g, 'current_user_id', None):
        return jsonify({'error': '不能删除当前登录用户'}), 400

    db.session.delete(u)
    db.session.commit()
    return jsonify({'message': 'User deleted'})


@users_bp.route('/auth/roles', methods=['GET'])
def list_roles():
    deny = _require_admin()
    if deny:
        return deny
    roles = Role.query.order_by(Role.name.asc()).all()
    return jsonify({'roles': [r.to_dict() for r in roles]})
