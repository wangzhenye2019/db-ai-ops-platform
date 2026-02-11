import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    BACKUP_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backups'))
    MAX_BACKUPS = int(os.getenv('MAX_BACKUPS', 10))

    # Celery settings
    broker_url = os.getenv('CELERY_BROKER', 'redis://localhost:6379/0')
    result_backend = os.getenv('CELERY_BACKEND', 'redis://localhost:6379/0')
    task_track_started = True
    task_time_limit = 30 * 60  # 30 minutes

    # Database settings (for storing backup records)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///backups.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # Backup settings
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', 30))

    @staticmethod
    def init_app(app):
        # Create backup folder if not exists
        os.makedirs(Config.BACKUP_FOLDER, exist_ok=True)
