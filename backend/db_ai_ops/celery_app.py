from celery.schedules import crontab

from db_ai_ops import create_app
from db_ai_ops.extensions import celery

flask_app = create_app()
celery.conf.update(flask_app.config)


class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask
celery.autodiscover_tasks(['db_ai_ops.tasks'])

__all__ = ['celery', 'crontab']
