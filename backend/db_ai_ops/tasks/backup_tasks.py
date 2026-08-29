import datetime
import hashlib
import os
import re
import subprocess

from db_ai_ops.config import Config
from db_ai_ops.extensions import celery, db
from db_ai_ops.models import Backup, BackupStatus, Database, DatabaseType
from db_ai_ops.security import open_private_output, run_argv


_IDENTIFIER = re.compile(r'^[A-Za-z0-9_$#.-]+$')


def _validate_identifier(value):
    if not isinstance(value, str) or not value or not _IDENTIFIER.fullmatch(value):
        raise ValueError('database identifier contains unsupported characters')
    return value


@celery.task
def backup_database(database_id, backup_type='full'):
    database = Database.query.get(database_id)
    if not database:
        return f"Database not found: {database_id}"

    backup = Backup(
        database_id=database_id,
        backup_type=backup_type,
        status=BackupStatus.RUNNING,
        started_at=datetime.datetime.utcnow()
    )
    db.session.add(backup)
    db.session.commit()

    try:
        if backup_type == 'incremental':
            if database.db_type == DatabaseType.MYSQL:
                result = backup_mysql_incremental(
                    database.database,
                    database.username,
                    database.password,
                    database.host,
                    database.port
                )
            else:
                raise Exception("Incremental backup only supported for MySQL currently")
        else:
            if database.db_type == DatabaseType.MYSQL:
                result = backup_mysql(
                    database.database,
                    database.username,
                    database.password,
                    database.host,
                    database.port
                )
            elif database.db_type == DatabaseType.POSTGRESQL:
                result = backup_postgres(
                    database.database,
                    database.username,
                    database.password,
                    database.host,
                    database.port
                )
            elif database.db_type == DatabaseType.ORACLE:
                result = backup_oracle(
                    database.database,
                    database.username,
                    database.password,
                    database.host,
                    database.port
                )
            elif database.db_type == DatabaseType.MSSQL:
                result = backup_mssql(
                    database.database,
                    database.username,
                    database.password,
                    database.host,
                    database.port
                )
            else:
                raise Exception(f"Unsupported database type: {database.db_type}")

        # Calculate checksum
        checksum = calculate_checksum(result.get('file_path', ''))

        backup.status = BackupStatus.SUCCESS
        backup.file_path = result.get('file_path')
        backup.file_size = result.get('file_size', 0)
        backup.completed_at = datetime.datetime.utcnow()
        backup.checksum = checksum
        db.session.commit()

        return f"Backup successful: {result['file_path']}"

    except Exception as e:
        backup.status = BackupStatus.FAILED
        backup.error_message = str(e)
        backup.completed_at = datetime.datetime.utcnow()
        db.session.commit()
        raise


@celery.task
def backup_mysql(database_name, user, password, host="localhost", port=3306):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.sql")

    env = os.environ.copy()
    env['MYSQL_PWD'] = password
    command = ['mysqldump', f'-h{host}', f'-P{port}', f'-u{user}', database_name]

    try:
        with open_private_output(backup_file) as output:
            run_argv(command, timeout=1800, stdout=output, env=env)
        file_size = os.path.getsize(backup_file)
        return {"file_path": backup_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (30 minutes)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"MySQL backup failed: {e}")


@celery.task
def backup_mysql_incremental(database_name, user, password, host="localhost", port=3306):
    """增量备份 - 使用mysqldump --single-transaction --master-data=2"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_inc_{timestamp}.sql")

    # 使用 --single-transaction 和 --master-data=2 获取binlog位置
    env = os.environ.copy()
    env['MYSQL_PWD'] = password
    command = ['mysqldump', f'-h{host}', f'-P{port}', f'-u{user}', '--single-transaction', '--master-data=2', database_name]

    try:
        with open_private_output(backup_file) as output:
            run_argv(command, timeout=1800, stdout=output, env=env)
        file_size = os.path.getsize(backup_file)
        return {"file_path": backup_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Incremental backup timeout (30 minutes)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"MySQL incremental backup failed: {e}")


@celery.task
def backup_postgres(database_name, user, password, host="localhost", port=5432):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.dump")

    env = os.environ.copy()
    env['PGPASSWORD'] = password

    command = ['pg_dump', '-h', host, '-p', str(port), '-U', user, '-F', 'c', '-f', backup_file, database_name]

    try:
        run_argv(command, timeout=1800, env=env)
        file_size = os.path.getsize(backup_file)
        return {"file_path": backup_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (30 minutes)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"PostgreSQL backup failed: {e}")


@celery.task
def backup_oracle(database_name, user, password, host="localhost", port=1521):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dmp_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.dmp")
    log_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.log")

    _validate_identifier(database_name)
    _validate_identifier(user)
    conn_string = f"{user}/{password}@{host}:{port}/{database_name}"
    command = ['expdp', conn_string, 'directory=DATA_PUMP_DIR', f'dumpfile={os.path.basename(dmp_file)}', f'logfile={os.path.basename(log_file)}', f'schemas={user}']

    try:
        run_argv(command, timeout=3600)
        file_size = os.path.getsize(dmp_file)
        return {"file_path": dmp_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (60 minutes)")
    except subprocess.CalledProcessError as e:
        old_dmp = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}_old.dmp")
        command = ['exp', conn_string, f'file={old_dmp}', f'log={log_file}']
        try:
            run_argv(command, timeout=3600)
            file_size = os.path.getsize(old_dmp)
            return {"file_path": old_dmp, "file_size": file_size}
        except Exception:
            raise Exception(f"Oracle backup failed: {e}")


@celery.task
def backup_mssql(database_name, user, password, host="localhost", port=1433):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.bak")

    _validate_identifier(database_name)
    sql_command = f"BACKUP DATABASE [{database_name}] TO DISK = N'{backup_file}' WITH NOFORMAT, NOINIT, NAME = N'{database_name}-Full Database Backup', SKIP, NOREWIND, NOUNLOAD, STATS = 10"
    command = ['sqlcmd', '-S', f'{host},{port}', '-U', user, '-P', password, '-Q', sql_command]

    try:
        run_argv(command, timeout=1800)
        file_size = os.path.getsize(backup_file)
        return {"file_path": backup_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (30 minutes)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"MSSQL backup failed: {e}")


@celery.task
def cleanup_old_backups():
    retention_days = Config.BACKUP_RETENTION_DAYS
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)

    old_backups = Backup.query.filter(Backup.completed_at < cutoff_date).all()
    deleted_count = 0

    for backup in old_backups:
        if backup.file_path and os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
                deleted_count += 1
            except OSError:
                pass
        db.session.delete(backup)

    db.session.commit()

    return f"Cleaned up {deleted_count} backup files older than {retention_days} days"


def calculate_checksum(file_path):
    """计算文件的MD5校验和"""
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


@celery.task
def verify_backup(backup_id):
    """验证备份文件完整性"""
    backup = Backup.query.get(backup_id)
    if not backup:
        return f"Backup not found: {backup_id}"

    if not backup.file_path or not os.path.exists(backup.file_path):
        backup.verify_status = 'failed'
        backup.verify_message = 'Backup file not found'
        db.session.commit()
        return 'Backup file not found'

    try:
        # 计算当前校验和
        current_checksum = calculate_checksum(backup.file_path)

        # 对比原有校验和
        if backup.checksum and current_checksum != backup.checksum:
            backup.verify_status = 'failed'
            backup.verify_message = f'Checksum mismatch: expected {backup.checksum}, got {current_checksum}'
            db.session.commit()
            return 'Checksum mismatch - backup may be corrupted'

        # 文件大小检查
        current_size = os.path.getsize(backup.file_path)
        if backup.file_size and current_size != backup.file_size:
            backup.verify_status = 'failed'
            backup.verify_message = f'Size mismatch: expected {backup.file_size}, got {current_size}'
            db.session.commit()
            return 'File size mismatch'

        backup.verify_status = 'verified'
        backup.verify_message = 'Backup verified successfully'
        backup.checksum = current_checksum  # 更新校验和
        db.session.commit()

        return 'Backup verified successfully'

    except Exception as e:
        backup.verify_status = 'failed'
        backup.verify_message = str(e)
        db.session.commit()
        raise


@celery.task
def restore_database(database_id, backup_id):
    """从备份恢复数据库"""
    database = Database.query.get(database_id)
    backup = Backup.query.get(backup_id)

    if not database:
        return f"Database not found: {database_id}"
    if not backup:
        return f"Backup not found: {backup_id}"
    if backup.status != BackupStatus.SUCCESS:
        return "Backup not completed successfully"
    if not backup.file_path or not os.path.exists(backup.file_path):
        return "Backup file not found"

    try:
        if database.db_type == DatabaseType.MYSQL:
            result = restore_mysql(
                database.database,
                database.username,
                database.password,
                database.host,
                database.port,
                backup.file_path
            )
        elif database.db_type == DatabaseType.POSTGRESQL:
            result = restore_postgres(
                database.database,
                database.username,
                database.password,
                database.host,
                database.port,
                backup.file_path
            )
        elif database.db_type == DatabaseType.ORACLE:
            result = restore_oracle(
                database.username,
                database.password,
                database.host,
                database.port,
                backup.file_path
            )
        else:
            raise Exception(f"Unsupported database type: {database.db_type}")

        return f"Restore successful: {result}"

    except Exception as e:
        raise Exception(f"Restore failed: {e}")


@celery.task
def restore_mysql(database_name, user, password, host, port, backup_file):
    """恢复MySQL数据库"""
    env = os.environ.copy()
    env['MYSQL_PWD'] = password
    try:
        with open(backup_file, 'rb') as source:
            run_argv(['mysql', f'-h{host}', f'-P{port}', f'-u{user}', database_name], timeout=3600, stdin=source, env=env)
        return f"Restored database {database_name} from {backup_file}"
    except subprocess.CalledProcessError as e:
        raise Exception(f"MySQL restore failed: {e}")


@celery.task
def restore_postgres(database_name, user, password, host, port, backup_file):
    """恢复PostgreSQL数据库"""
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    command = ['pg_restore', '-h', host, '-p', str(port), '-U', user, '-d', database_name, '-c', backup_file]
    try:
        run_argv(command, timeout=3600, env=env)
        return f"Restored database {database_name} from {backup_file}"
    except subprocess.CalledProcessError as e:
        raise Exception(f"PostgreSQL restore failed: {e}")


@celery.task
def restore_oracle(user, password, host, port, backup_file):
    """恢复Oracle数据库"""
    _validate_identifier(user)
    conn_string = f"{user}/{password}@{host}:{port}"
    command = ['impdp', conn_string, 'directory=DATA_PUMP_DIR', f'dumpfile={os.path.basename(backup_file)}', 'table_exists_action=replace']
    try:
        run_argv(command, timeout=3600)
        return f"Restored from {backup_file}"
    except subprocess.CalledProcessError as e:
        # 尝试使用imp
        old_command = ['imp', conn_string, f'file={backup_file}', 'full=y']
        try:
            run_argv(old_command, timeout=3600)
            return f"Restored from {backup_file}"
        except Exception:
            raise Exception(f"Oracle restore failed: {e}")
