from flask import Flask, jsonify, request, g
from flask_cors import CORS

from .config import Config
from .extensions import db
from .auth import verify_token


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    @app.before_request
    def _auth_guard():
        if request.method == 'OPTIONS':
            return None
        if not request.path.startswith('/api'):
            return None
        if request.path == '/api/auth/login':
            return None

        auth_header = request.headers.get('Authorization') or ''
        token = auth_header[7:] if auth_header.startswith('Bearer ') else None
        if not token:
            return jsonify({'error': 'Unauthorized'}), 401

        username = verify_token(app.config['SECRET_KEY'], token)
        if not username:
            return jsonify({'error': 'Unauthorized'}), 401

        g.current_user = username
        return None

    with app.app_context():
        from . import models

        db.create_all()

        from .api import backup_bp, schedule_bp, database_bp, auth_bp

        app.register_blueprint(backup_bp, url_prefix='/api')
        app.register_blueprint(schedule_bp, url_prefix='/api')
        app.register_blueprint(database_bp, url_prefix='/api')
        app.register_blueprint(auth_bp, url_prefix='/api')

    Config.init_app(app)
    return app


__all__ = ['create_app', 'Config']
