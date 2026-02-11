import subprocess
import os
import datetime
from celery import shared_task
from app import db, Config
from app.models import Backup, BackupStatus, DatabaseType


@shared_task
def backup_database(database_id):
    """Generic backup task - dispatches to appropriate database type"""
    database = Database.query.get(database_id)
    if not database:
        return f"Database not found: {database_id}"

    # Create backup record
    backup = Backup(
        database_id=database_id,
        status=BackupStatus.RUNNING,
        started_at=datetime.datetime.utcnow()
    )
    db.session.add(backup)
    db.session.commit()

    try:
        # Dispatch to specific backup function
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

        # Update backup record
        backup.status = BackupStatus.SUCCESS
        backup.file_path = result.get('file_path')
        backup.file_size = result.get('file_size', 0)
        backup.completed_at = datetime.datetime.utcnow()
        db.session.commit()

        return f"Backup successful: {result['file_path']}"

    except Exception as e:
        # Update backup record with error
        backup.status = BackupStatus.FAILED
        backup.error_message = str(e)
        backup.completed_at = datetime.datetime.utcnow()
        db.session.commit()
        raise


@shared_task
def backup_mysql(database_name, user, password, host="localhost", port=3306):
    """MySQL backup using mysqldump"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.sql")

    command = f"mysqldump -h{host} -P{port} -u{user} -p{password} {database_name} > {backup_file}"

    try:
        subprocess.run(command, shell=True, check=True, timeout=1800)
        file_size = os.path.getsize(backup_file)
        return {"file_path": backup_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (30 minutes)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"MySQL backup failed: {e}")


@shared_task
def backup_postgres(database_name, user, password, host="localhost", port=5432):
    """PostgreSQL backup using pg_dump"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.dump")

    # Set PGPASSWORD environment variable for pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = password

    command = f"pg_dump -h {host} -p {port} -U {user} -F c -f {backup_file} {database_name}"

    try:
        subprocess.run(command, shell=True, check=True, timeout=1800, env=env)
        file_size = os.path.getsize(backup_file)
        return {"file_path": backup_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (30 minutes)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"PostgreSQL backup failed: {e}")


@shared_task
def backup_oracle(database_name, user, password, host="localhost", port=1521):
    """Oracle backup using expdp (Data Pump)"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dmp_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.dmp")
    log_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.log")

    # Oracle connection string
    conn_string = f"{user}/{password}@{host}:{port}/{database_name}"

    command = f"expdp {conn_string} directory=DATA_PUMP_DIR dumpfile={os.path.basename(dmp_file)} logfile={os.path.basename(log_file)} schemas={user}"

    try:
        subprocess.run(command, shell=True, check=True, timeout=3600)
        file_size = os.path.getsize(dmp_file)
        return {"file_path": dmp_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (60 minutes)")
    except subprocess.CalledProcessError as e:
        # Try exp as fallback (deprecated but works without Data Pump)
        old_dmp = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}_old.dmp")
        command = f"exp {conn_string} file={old_dmp} log={log_file}"
        try:
            subprocess.run(command, shell=True, check=True, timeout=3600)
            file_size = os.path.getsize(old_dmp)
            return {"file_path": old_dmp, "file_size": file_size}
        except:
            raise Exception(f"Oracle backup failed: {e}")


@shared_task
def backup_mssql(database_name, user, password, host="localhost", port=1433):
    """SQL Server backup using sqlcmd"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_FOLDER, f"{database_name}_{timestamp}.bak")

    # Build SQL backup command
    sql_command = f"BACKUP DATABASE [{database_name}] TO DISK = N'{backup_file}' WITH NOFORMAT, NOINIT, NAME = N'{database_name}-Full Database Backup', SKIP, NOREWIND, NOUNLOAD, STATS = 10"

    command = f'sqlcmd -S {host},{port} -U {user} -P {password} -Q "{sql_command}"'

    try:
        subprocess.run(command, shell=True, check=True, timeout=1800)
        file_size = os.path.getsize(backup_file)
        return {"file_path": backup_file, "file_size": file_size}
    except subprocess.TimeoutExpired:
        raise Exception("Backup timeout (30 minutes)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"MSSQL backup failed: {e}")


@shared_task
def cleanup_old_backups():
    """Clean up old backup files based on retention policy"""
    from app.models import Backup

    retention_days = Config.BACKUP_RETENTION_DAYS
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)

    # Find and delete old backups from database
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
