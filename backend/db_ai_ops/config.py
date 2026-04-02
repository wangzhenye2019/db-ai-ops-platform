import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))

    BACKUP_FOLDER = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'backups')
    )
    MAX_BACKUPS = int(os.getenv('MAX_BACKUPS', 10))
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', 30))

    broker_url = os.getenv('CELERY_BROKER', 'redis://localhost:6379/0')
    result_backend = os.getenv('CELERY_BACKEND', 'redis://localhost:6379/0')
    task_track_started = True
    task_time_limit = 30 * 60
    task_always_eager = os.getenv('CELERY_ALWAYS_EAGER', '0') == '1'
    task_eager_propagates = True

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///backups.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    XXL_JOB_ADMIN_ADDRESSES = os.getenv('XXL_JOB_ADMIN_ADDRESSES', '')
    XXL_JOB_ACCESS_TOKEN = os.getenv('XXL_JOB_ACCESS_TOKEN', '')
    XXL_JOB_LOG_FOLDER = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'xxl-job')
    )

    @staticmethod
    def init_app(app):
        os.makedirs(Config.BACKUP_FOLDER, exist_ok=True)
        os.makedirs(Config.XXL_JOB_LOG_FOLDER, exist_ok=True)
