# Backend Development Rules (Flask & Celery)

## 🐍 Python Standards
- **Async First**: Use Celery tasks for heavy O&M operations (Backup, Restore, Tuning).
- **ORM**: Use SQLAlchemy for model definitions in `models.py`.
- **Driver Safety**: Handle database-specific client requirements (e.g., `expdp` for Oracle, `mysqldump` for MySQL).

## 🔒 Security & Reliability
- **Error Handling**: Every O&M task must have comprehensive `try-except` blocks with logging to Redis/Celery results.
- **Path Handling**: Use `pathlib` for managing backup file paths in the `backups/` directory.
- **Env Vars**: Never hardcode secrets; use `.env` and `config.py`.