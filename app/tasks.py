import subprocess
from app import create_app, make_celery
from celery import shared_task

# Initialize the app and celery
app = create_app()
celery = make_celery(app)


# MySQL backup task
@shared_task
def backup_mysql(database_name, user, password, host="localhost"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{app.config['BACKUP_FOLDER']}/{database_name}_{timestamp}.sql"
    command = f"mysqldump -u{user} -p{password} -h{host} {database_name} > {backup_file}"

    try:
        subprocess.run(command, shell=True, check=True)
        return f"Backup successful: {backup_file}"
    except subprocess.CalledProcessError as e:
        return f"Backup failed: {e}"


# PostgreSQL backup task
@shared_task
def backup_postgres(database_name, user, password, host="localhost"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{app.config['BACKUP_FOLDER']}/{database_name}_{timestamp}.dump"
    command = f"pg_dump -U {user} -h {host} -F c -f {backup_file} {database_name}"

    try:
        subprocess.run(command, shell=True, check=True)
        return f"Backup successful: {backup_file}"
    except subprocess.CalledProcessError as e:
        return f"Backup failed: {e}"

# More tasks can be added for other DB types (SQL Server, Oracle) similarly.
