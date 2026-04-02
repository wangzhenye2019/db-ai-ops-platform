from flask import Blueprint, current_app, jsonify, request

from db_ai_ops.auth import admin_username, issue_token, verify_admin_password
from db_ai_ops.extensions import db
from db_ai_ops.models import User

auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    user = User.query.filter_by(username=username).first()
    if user and user.enabled and user.check_password(password):
        token = issue_token(current_app.config['SECRET_KEY'], user.id, user.username)
        return jsonify({
            'token': token,
            'user': user.to_dict()
        })

    if username != admin_username() or not verify_admin_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, enabled=True, password_hash='x')
        user.set_password(password)
        db_role = None
        try:
            from db_ai_ops.models import Role
            db_role = Role.query.filter_by(name='admin').first()
        except Exception:
            db_role = None
        if db_role:
            user.roles = [db_role]
        db.session.add(user)
        db.session.commit()

    token = issue_token(current_app.config['SECRET_KEY'], user.id, user.username)
    return jsonify({
        'token': token,
        'user': user.to_dict()
    })


@auth_bp.route('/auth/me', methods=['GET'])
def me():
    from flask import g

    return jsonify({
        'user': {
            'id': getattr(g, 'current_user_id', None),
            'username': getattr(g, 'current_user', None),
            'roles': getattr(g, 'current_roles', [])
        }
    })
