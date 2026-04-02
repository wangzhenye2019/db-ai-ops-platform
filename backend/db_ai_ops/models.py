from datetime import datetime
import enum

from db_ai_ops.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash


user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = db.relationship('Role', secondary=user_roles, lazy='subquery', backref=db.backref('users', lazy=True))

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def role_names(self):
        return [r.name for r in (self.roles or [])]

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'enabled': self.enabled,
            'roles': self.role_names(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class DatabaseType(enum.Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    MSSQL = "mssql"


class Database(db.Model):
    __tablename__ = 'databases'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    db_type = db.Column(db.Enum(DatabaseType), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    database = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    __tablename__ = 'backups'

    id = db.Column(db.Integer, primary_key=True)
    database_id = db.Column(db.Integer, db.ForeignKey('databases.id'), nullable=False)
    status = db.Column(db.Enum(BackupStatus), default=BackupStatus.PENDING)
    file_path = db.Column(db.String(512))
    file_size = db.Column(db.BigInteger)
    task_id = db.Column(db.String(255))
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
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    database_id = db.Column(db.Integer, db.ForeignKey('databases.id'), nullable=False)
    cron_expression = db.Column(db.String(100), nullable=False)
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


class HostOSType(enum.Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    UNIX = "unix"
    NETWORK = "network"
    OTHER = "other"


class Host(db.Model):
    __tablename__ = 'hosts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=22)
    os_type = db.Column(db.Enum(HostOSType), nullable=False, default=HostOSType.LINUX)
    username = db.Column(db.String(100))
    password = db.Column(db.String(255))
    tags = db.Column(db.JSON)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'os_type': self.os_type.value if self.os_type else None,
            'username': self.username,
            'enabled': self.enabled,
            'tags': self.tags or [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class MiddlewareType(enum.Enum):
    REDIS = "redis"
    MONGODB = "mongodb"
    ELASTICSEARCH = "elasticsearch"
    KAFKA = "kafka"
    RABBITMQ = "rabbitmq"
    ZOOKEEPER = "zookeeper"
    NGINX = "nginx"
    OTHER = "other"


class Middleware(db.Model):
    __tablename__ = 'middlewares'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mw_type = db.Column(db.Enum(MiddlewareType), nullable=False, default=MiddlewareType.OTHER)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    version = db.Column(db.String(50))
    enabled = db.Column(db.Boolean, default=True)
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'mw_type': self.mw_type.value if self.mw_type else None,
            'host': self.host,
            'port': self.port,
            'version': self.version,
            'enabled': self.enabled,
            'meta': self.meta or {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class KnowledgeScope(enum.Enum):
    SERVER = "server"
    MIDDLEWARE = "middleware"
    DATABASE = "database"
    GENERAL = "general"


class KnowledgeArticle(db.Model):
    __tablename__ = 'knowledge_articles'

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.Enum(KnowledgeScope), nullable=False, default=KnowledgeScope.GENERAL)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    tags = db.Column(db.JSON)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'scope': self.scope.value if self.scope else None,
            'title': self.title,
            'category': self.category,
            'tags': self.tags or [],
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class OperationTaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class OperationTask(db.Model):
    __tablename__ = 'operation_tasks'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.JSON)
    result = db.Column(db.JSON)
    status = db.Column(db.Enum(OperationTaskStatus), nullable=False, default=OperationTaskStatus.PENDING)
    error_message = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'action': self.action,
            'payload': self.payload or {},
            'result': self.result or {},
            'status': self.status.value if self.status else None,
            'error_message': self.error_message,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class InspectionReportStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


class InspectionReport(db.Model):
    __tablename__ = 'inspection_reports'

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.String(50), nullable=False)
    target_summary = db.Column(db.String(255))
    result = db.Column(db.JSON)
    status = db.Column(db.Enum(InspectionReportStatus), nullable=False, default=InspectionReportStatus.PENDING)
    error_message = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'scope': self.scope,
            'target_summary': self.target_summary,
            'result': self.result or {},
            'status': self.status.value if self.status else None,
            'error_message': self.error_message,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    method = db.Column(db.String(10))
    path = db.Column(db.String(512))
    status_code = db.Column(db.Integer)
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'method': self.method,
            'path': self.path,
            'status_code': self.status_code,
            'ip': self.ip,
            'created_at': self.created_at.isoformat()
        }


class AssetType(enum.Enum):
    HOST = "host"
    DATABASE = "database"
    MIDDLEWARE = "middleware"


class AssetGroup(db.Model):
    __tablename__ = 'asset_groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = db.relationship('AssetGroupMember', backref='group', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class AssetGroupMember(db.Model):
    __tablename__ = 'asset_group_members'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('asset_groups.id'), nullable=False)
    asset_type = db.Column(db.Enum(AssetType), nullable=False)
    asset_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('group_id', 'asset_type', 'asset_id', name='uq_group_asset'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'asset_type': self.asset_type.value if self.asset_type else None,
            'asset_id': self.asset_id,
            'created_at': self.created_at.isoformat()
        }
