from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    with app.app_context():
        from . import models

        db.create_all()

        from .api import backup_bp, schedule_bp, database_bp

        app.register_blueprint(backup_bp, url_prefix='/api')
        app.register_blueprint(schedule_bp, url_prefix='/api')
        app.register_blueprint(database_bp, url_prefix='/api')

    Config.init_app(app)
    return app


__all__ = ['create_app', 'Config']
