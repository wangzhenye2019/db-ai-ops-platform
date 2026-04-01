# 数据库AI自动化运维平台（后端）

后端为 Flask + SQLAlchemy + Celery 的 API 服务，默认使用 SQLite 存储平台自身数据（数据库清单、备份记录、定时任务等）。

## 本地运行（Windows / Linux / macOS）

```bash
cd backend
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Linux / macOS：

```bash
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Celery（可选）

无 Redis 也想调试任务时，可以让 Celery 同步执行：

```bash
set CELERY_ALWAYS_EAGER=1
```

或（Linux / macOS）：

```bash
export CELERY_ALWAYS_EAGER=1
```

有 Redis 时，启动 worker/beat：

```bash
celery -A db_ai_ops.celery_app:celery worker --loglevel=info
celery -A db_ai_ops.celery_app:celery beat --loglevel=info
```

## 数据库驱动（按需安装）

需要连接/备份对应数据库时，再安装驱动：

```bash
pip install -r requirements-drivers.txt
```
