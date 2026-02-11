from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
from .config import Config

# Initialize extensions
db = SQLAlchemy()
celery = None

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # Initialize Celery
    global celery
    celery = make_celery(app)

    # Import models and routes
    with app.app_context():
        from . import models
        db.create_all()

        from .api import backup_bp, schedule_bp, database_bp
        app.register_blueprint(backup_bp, url_prefix='/api')
        app.register_blueprint(schedule_bp, url_prefix='/api')
        app.register_blueprint(database_bp, url_prefix='/api')

    Config.init_app(app)
    return app

def make_celery(app):
    """Create Celery instance with Flask context"""
    celery = Celery(
        app.import_name,
        backend=app.config['result_backend'],
        broker=app.config['broker_url']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Make tasks aware of Flask context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
