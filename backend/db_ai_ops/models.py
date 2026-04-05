from datetime import datetime
import enum

from db_ai_ops.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash


user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)


class Permission(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50))  # 如: system, backup, monitor, sql
    description = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'category': self.category,
            'description': self.description
        }


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': [p.code for p in (self.permissions or [])]
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

    def has_permission(self, permission_code):
        """检查用户是否拥有某权限"""
        for role in (self.roles or []):
            for perm in (role.permissions or []):
                if perm.code == permission_code:
                    return True
        return False

    def get_all_permissions(self):
        """获取用户所有权限"""
        perms = set()
        for role in (self.roles or []):
            for perm in (role.permissions or []):
                perms.add(perm.code)
        return list(perms)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'enabled': self.enabled,
            'roles': self.role_names(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class BusinessSystem(db.Model):
    __tablename__ = 'business_systems'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    code = db.Column(db.String(60), unique=True)
    owner = db.Column(db.String(100))
    owner_contact = db.Column(db.String(100))
    description = db.Column(db.String(255))
    tags = db.Column(db.JSON)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'owner': self.owner,
            'owner_contact': self.owner_contact,
            'description': self.description,
            'tags': self.tags or [],
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class BusinessContact(db.Model):
    __tablename__ = 'business_contacts'

    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey('business_systems.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    remark = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    system = db.relationship('BusinessSystem', lazy='joined', backref=db.backref('contacts', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'system_id': self.system_id,
            'name': self.name,
            'role': self.role,
            'phone': self.phone,
            'email': self.email,
            'remark': self.remark,
            'created_at': self.created_at.isoformat()
        }


class CredentialType(enum.Enum):
    SSH_PASSWORD = "ssh_password"
    DB_PASSWORD = "db_password"
    GENERIC = "generic"


class Credential(db.Model):
    __tablename__ = 'credentials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    cred_type = db.Column(db.Enum(CredentialType), nullable=False, default=CredentialType.GENERIC)
    username = db.Column(db.String(100))
    secret_encrypted = db.Column(db.Text, nullable=False)
    business_system_id = db.Column(db.Integer, db.ForeignKey('business_systems.id'))
    owner = db.Column(db.String(100))
    tags = db.Column(db.JSON)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business_system = db.relationship('BusinessSystem', lazy='joined')

    def to_safe_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cred_type': self.cred_type.value if self.cred_type else None,
            'username': self.username,
            'business_system_id': self.business_system_id,
            'business_system_name': self.business_system.name if self.business_system else None,
            'owner': self.owner,
            'tags': self.tags or [],
            'enabled': self.enabled,
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
    credential_id = db.Column(db.Integer, db.ForeignKey('credentials.id'))
    business_system_id = db.Column(db.Integer, db.ForeignKey('business_systems.id'))
    owner = db.Column(db.String(100))
    env = db.Column(db.String(50))
    version = db.Column(db.String(50))
    remark = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business_system = db.relationship('BusinessSystem', lazy='joined')
    credential = db.relationship('Credential', lazy='joined')
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
            'credential_id': self.credential_id,
            'business_system_id': self.business_system_id,
            'business_system_name': self.business_system.name if self.business_system else None,
            'owner': self.owner,
            'env': self.env,
            'version': self.version,
            'remark': self.remark,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class BackupStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INCREMENTAL = "incremental"


class Backup(db.Model):
    __tablename__ = 'backups'

    id = db.Column(db.Integer, primary_key=True)
    database_id = db.Column(db.Integer, db.ForeignKey('databases.id'), nullable=False)
    backup_type = db.Column(db.String(20), default='full')  # full/incremental
    status = db.Column(db.Enum(BackupStatus), default=BackupStatus.PENDING)
    file_path = db.Column(db.String(512))
    file_size = db.Column(db.BigInteger)
    task_id = db.Column(db.String(255))
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verify_status = db.Column(db.String(20))  # pending/verified/failed
    verify_message = db.Column(db.Text)
    checksum = db.Column(db.String(64))

    def to_dict(self):
        return {
            'id': self.id,
            'database_id': self.database_id,
            'backup_type': self.backup_type,
            'status': self.status.value,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'task_id': self.task_id,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat(),
            'verify_status': self.verify_status,
            'verify_message': self.verify_message,
            'checksum': self.checksum
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
    hostname = db.Column(db.String(255))
    os_version = db.Column(db.String(100))
    username = db.Column(db.String(100))
    password = db.Column(db.String(255))
    credential_id = db.Column(db.Integer, db.ForeignKey('credentials.id'))
    business_system_id = db.Column(db.Integer, db.ForeignKey('business_systems.id'))
    owner = db.Column(db.String(100))
    env = db.Column(db.String(50))
    idc = db.Column(db.String(100))
    remark = db.Column(db.String(255))
    tags = db.Column(db.JSON)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business_system = db.relationship('BusinessSystem', lazy='joined')
    credential = db.relationship('Credential', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'os_type': self.os_type.value if self.os_type else None,
            'hostname': self.hostname,
            'os_version': self.os_version,
            'username': self.username,
            'credential_id': self.credential_id,
            'business_system_id': self.business_system_id,
            'business_system_name': self.business_system.name if self.business_system else None,
            'owner': self.owner,
            'env': self.env,
            'idc': self.idc,
            'remark': self.remark,
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
    credential_id = db.Column(db.Integer, db.ForeignKey('credentials.id'))
    business_system_id = db.Column(db.Integer, db.ForeignKey('business_systems.id'))
    owner = db.Column(db.String(100))
    env = db.Column(db.String(50))
    remark = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business_system = db.relationship('BusinessSystem', lazy='joined')
    credential = db.relationship('Credential', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'mw_type': self.mw_type.value if self.mw_type else None,
            'host': self.host,
            'port': self.port,
            'version': self.version,
            'credential_id': self.credential_id,
            'business_system_id': self.business_system_id,
            'business_system_name': self.business_system.name if self.business_system else None,
            'owner': self.owner,
            'env': self.env,
            'remark': self.remark,
            'enabled': self.enabled,
            'meta': self.meta or {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class MetricType(enum.Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    CONNECTIONS = "connections"
    QPS = "qps"
    TPS = "tps"
    SLOW_QUERIES = "slow_queries"
    THREADS = "threads"


class MetricHistory(db.Model):
    __tablename__ = 'metric_history'

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(20), nullable=False)  # host/database/middleware
    target_id = db.Column(db.Integer, nullable=False)
    metric_type = db.Column(db.String(30), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'metric_type': self.metric_type,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat()
        }


class Prediction(db.Model):
    """预测数据模型"""
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(20), nullable=False)  # host/database/middleware
    target_id = db.Column(db.Integer, nullable=False)
    metric_type = db.Column(db.String(30), nullable=False)  # disk/connections/capacity
    predicted_value = db.Column(db.Float)  # 预测值
    predicted_at = db.Column(db.DateTime)  # 预测时间
    threshold_value = db.Column(db.Float)  # 阈值
    threshold_day = db.Column(db.Integer)  # 预计到达阈值的天数
    confidence = db.Column(db.Float)  # 置信度
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'metric_type': self.metric_type,
            'predicted_value': self.predicted_value,
            'predicted_at': self.predicted_at.isoformat() if self.predicted_at else None,
            'threshold_value': self.threshold_value,
            'threshold_day': self.threshold_day,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat()
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


class SlowQuery(db.Model):
    """慢SQL记录"""
    __tablename__ = 'slow_queries'

    id = db.Column(db.Integer, primary_key=True)
    database_id = db.Column(db.Integer, db.ForeignKey('databases.id'))
    db_type = db.Column(db.String(20))  # mysql/postgresql/oracle/mssql
    sql_text = db.Column(db.Text)
    execute_time = db.Column(db.Float)  # seconds
    rows_sent = db.Column(db.Integer)
    rows_examined = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(100))
    client = db.Column(db.String(100))
    digest = db.Column(db.String(64))  # SQL摘要
    analysis = db.Column(db.JSON)  # 分析结果
    suggestion = db.Column(db.Text)  # 优化建议

    database = db.relationship('Database', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'database_id': self.database_id,
            'database_name': self.database.name if self.database else None,
            'db_type': self.db_type,
            'sql_text': self.sql_text,
            'execute_time': self.execute_time,
            'rows_sent': self.rows_sent,
            'rows_examined': self.rows_examined,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user': self.user,
            'client': self.client,
            'digest': self.digest,
            'analysis': self.analysis or {},
            'suggestion': self.suggestion
        }


class AgentRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class AgentSession(db.Model):
    __tablename__ = 'agent_sessions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    state = db.Column(db.JSON)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship('AgentMessage', backref='session', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'state': self.state or {},
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class AgentMessage(db.Model):
    __tablename__ = 'agent_messages'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('agent_sessions.id'), nullable=False, index=True)
    role = db.Column(db.Enum(AgentRole), nullable=False)
    content = db.Column(db.Text)
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role.value if self.role else None,
            'content': self.content,
            'meta': self.meta or {},
            'created_at': self.created_at.isoformat()
        }


class AssetType(enum.Enum):
    HOST = "host"
    DATABASE = "database"
    MIDDLEWARE = "middleware"
    IP = "ip"


class AssetSystemLink(db.Model):
    __tablename__ = 'asset_system_links'

    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey('business_systems.id'), nullable=False)
    asset_type = db.Column(db.Enum(AssetType), nullable=False)
    asset_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('system_id', 'asset_type', 'asset_id', name='uq_system_asset'),
    )

    system = db.relationship('BusinessSystem', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'system_id': self.system_id,
            'asset_type': self.asset_type.value if self.asset_type else None,
            'asset_id': self.asset_id,
            'created_at': self.created_at.isoformat()
        }


class TagCategory(enum.Enum):
    ASSET = "asset"
    SYSTEM = "system"


class TagDict(db.Model):
    __tablename__ = 'tag_dicts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    category = db.Column(db.Enum(TagCategory), nullable=False, default=TagCategory.ASSET)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category.value if self.category else None,
            'created_at': self.created_at.isoformat()
        }


class IdcDict(db.Model):
    __tablename__ = 'idc_dicts'

    id = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(60))
    name = db.Column(db.String(100), unique=True, nullable=False)
    remark = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'region': self.region,
            'name': self.name,
            'remark': self.remark,
            'created_at': self.created_at.isoformat()
        }


class IpVersion(enum.Enum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"


class IpStatus(enum.Enum):
    FREE = "free"
    RESERVED = "reserved"
    ALLOCATED = "allocated"


class IpAsset(db.Model):
    __tablename__ = 'ip_assets'

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), unique=True, nullable=False)
    cidr = db.Column(db.Integer)
    version = db.Column(db.Enum(IpVersion), nullable=False, default=IpVersion.IPV4)
    status = db.Column(db.Enum(IpStatus), nullable=False, default=IpStatus.FREE)
    business_system_id = db.Column(db.Integer, db.ForeignKey('business_systems.id'))
    owner = db.Column(db.String(100))
    env = db.Column(db.String(50))
    idc_id = db.Column(db.Integer, db.ForeignKey('idc_dicts.id'))
    remark = db.Column(db.String(255))
    tags = db.Column(db.JSON)
    assigned_asset_type = db.Column(db.Enum(AssetType))
    assigned_asset_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business_system = db.relationship('BusinessSystem', lazy='joined')
    idc = db.relationship('IdcDict', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'cidr': self.cidr,
            'version': self.version.value if self.version else None,
            'status': self.status.value if self.status else None,
            'business_system_id': self.business_system_id,
            'business_system_name': self.business_system.name if self.business_system else None,
            'owner': self.owner,
            'env': self.env,
            'idc_id': self.idc_id,
            'idc_name': self.idc.name if self.idc else None,
            'remark': self.remark,
            'tags': self.tags or [],
            'assigned_asset_type': self.assigned_asset_type.value if self.assigned_asset_type else None,
            'assigned_asset_id': self.assigned_asset_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


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


class XxlJobTrigger(db.Model):
    __tablename__ = 'xxl_job_triggers'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.BigInteger, index=True)
    log_id = db.Column(db.BigInteger, unique=True, index=True, nullable=False)
    log_datetime = db.Column(db.BigInteger)
    executor_handler = db.Column(db.String(200), nullable=False)
    executor_params = db.Column(db.JSON)
    executor_params_raw = db.Column(db.Text)
    status = db.Column(db.String(20), default='queued', nullable=False)
    celery_task_id = db.Column(db.String(64))
    handle_code = db.Column(db.Integer)
    handle_msg = db.Column(db.Text)
    log_file = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
