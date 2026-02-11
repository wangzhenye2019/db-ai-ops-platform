from flask import Flask
from celery import Celery

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Celery setup
    app.config.from_object('config.CeleryConfig')
    celery = make_celery(app)

    # Import views (API routes)
    from app import views

    return app

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['result_backend'],
        broker=app.config['broker_url']
    )
    celery.conf.update(app.config)
    return celery
