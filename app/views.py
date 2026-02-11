from flask import jsonify, request
from app import app
from app.tasks import backup_mysql, backup_postgres

@app.route('/backup/mysql', methods=['POST'])
def backup_mysql_api():
    data = request.get_json()
    result = backup_mysql.apply_async(args=[data['database'], data['user'], data['password']])
    return jsonify({"status": "Backup started", "task_id": result.id})

@app.route('/backup/postgres', methods=['POST'])
def backup_postgres_api():
    data = request.get_json()
    result = backup_postgres.apply_async(args=[data['database'], data['user'], data['password']])
    return jsonify({"status": "Backup started", "task_id": result.id})
