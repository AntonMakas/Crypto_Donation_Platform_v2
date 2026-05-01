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
import logging

from celery import Celery
from celery.signals import worker_ready
from kombu import Exchange, Queue

logger = logging.getLogger(__name__)

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


@app.on_after_finalize.connect
def log_registered_tasks(sender, **kwargs):
    """Log the task registry after Celery finalizes task discovery."""
    task_names = sorted(
        name for name in sender.tasks.keys()
        if not name.startswith("celery.")
    )
    logger.info("Celery finalized with %d registered app task(s)", len(task_names))
    logger.info("Celery registered tasks: %s", ", ".join(task_names))


@worker_ready.connect
def log_worker_runtime_state(sender=None, **kwargs):
    """Log the worker's queue and routing configuration once it's ready."""
    app_instance = getattr(sender, "app", app)
    queue_names = [queue.name for queue in app_instance.conf.task_queues or ()]
    logger.info(
        "Celery worker ready: default_queue=%s queues=%s routes=%s",
        app_instance.conf.task_default_queue,
        queue_names,
        app_instance.conf.task_routes,
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Utility task for checking worker connectivity."""
    print(f"Request: {self.request!r}")
