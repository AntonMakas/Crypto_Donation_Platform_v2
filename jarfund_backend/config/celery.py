"""
Celery application configuration for JarFund.

Workers are used for:
  - Background blockchain transaction verification
  - Periodic jar status updates
  - Any future async tasks

Start a worker:
    celery -A config.celery worker --loglevel=info

Start the beat scheduler (periodic tasks):
    celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

Flower monitoring (optional):
    celery -A config.celery flower
"""
import os
from celery import Celery
from kombu import Exchange, Queue

# Default to local settings in dev
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("jarfund")

# Read config from Django settings, namespaced by CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Belt-and-suspenders: declare the default queue at the app level so Kombu
# binds the worker to it before any task is dispatched, regardless of the
# order in which Django settings are loaded.
app.conf.task_default_queue = "celery"
app.conf.task_default_exchange = "celery"
app.conf.task_default_routing_key = "celery"
app.conf.task_queues = (
    Queue("celery", Exchange("celery"), routing_key="celery"),
)

# Explicit task routing — ensures all tasks go to the correct queue
app.conf.task_routes = {
    'apps.blockchain.tasks.*': {'queue': 'celery'},
    'apps.jars.tasks.*': {'queue': 'celery'},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Utility task for checking worker connectivity."""
    print(f"Request: {self.request!r}")
