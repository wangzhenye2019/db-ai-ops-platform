import os


class Config:
    SECRET_KEY = os.urandom(24)
    BACKUP_FOLDER = "./backups"


class CeleryConfig:
    broker_url = 'redis://localhost:6379/0'
    result_backend = 'redis://localhost:6379/0'
