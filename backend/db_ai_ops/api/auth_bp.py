from flask import Blueprint, current_app, jsonify, request

from db_ai_ops.auth import admin_username, issue_token, verify_admin_password

auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    if username != admin_username() or not verify_admin_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401

    token = issue_token(current_app.config['SECRET_KEY'], username)
    return jsonify({
        'token': token,
        'user': {
            'username': username,
            'role': 'admin'
        }
    })


@auth_bp.route('/auth/me', methods=['GET'])
def me():
    from flask import g

    return jsonify({
        'user': {
            'username': getattr(g, 'current_user', None),
            'role': 'admin'
        }
    })
