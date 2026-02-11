from datetime import datetime
from app import db
import enum

class DatabaseType(enum.Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    MSSQL = "mssql"

class Database(db.Model):
    """Database connection configuration"""
    __tablename__ = 'databases'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Display name
    db_type = db.Column(db.Enum(DatabaseType), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    database = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Should be encrypted in production
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    backups = db.relationship('Backup', backref='database', lazy=True, cascade='all, delete-orphan')
    schedules = db.relationship('Schedule', backref='database', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'db_type': self.db_type.value,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class BackupStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class Backup(db.Model):
    """Backup record"""
    __tablename__ = 'backups'

    id = db.Column(db.Integer, primary_key=True)
    database_id = db.Column(db.Integer, db.ForeignKey('databases.id'), nullable=False)
    status = db.Column(db.Enum(BackupStatus), default=BackupStatus.PENDING)
    file_path = db.Column(db.String(512))
    file_size = db.Column(db.BigInteger)
    task_id = db.Column(db.String(255))  # Celery task ID
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'database_id': self.database_id,
            'status': self.status.value,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'task_id': self.task_id,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat()
        }

class Schedule(db.Model):
    """Backup schedule"""
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    database_id = db.Column(db.Integer, db.ForeignKey('databases.id'), nullable=False)
    cron_expression = db.Column(db.String(100), nullable=False)  # Cron format: "0 2 * * *"
    enabled = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'database_id': self.database_id,
            'cron_expression': self.cron_expression,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'created_at': self.created_at.isoformat()
        }
