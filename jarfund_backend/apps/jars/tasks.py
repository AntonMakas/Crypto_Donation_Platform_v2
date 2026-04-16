"""
Celery tasks for the jars app.

update_expired_jar_statuses — runs every 60 s via beat.
Finds all Active jars whose deadline has passed and marks them Expired.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="apps.jars.tasks.update_expired_jar_statuses",
)
def update_expired_jar_statuses(self):
    """
    Periodic task: scan for Active jars whose deadline has passed
    and transition them to Expired.

    Runs every 60 seconds via Celery Beat.
    """
    from apps.jars.models import Jar, JarStatus

    try:
        now = timezone.now()

        # Find all Active jars whose deadline has passed
        # and whose target has NOT been reached (those are Completed)
        expired_qs = Jar.objects.filter(
            status=JarStatus.ACTIVE,
            deadline__lte=now,
        ).exclude(
            amount_raised_matic__gte=models.F("target_amount_matic")
        )

        count = expired_qs.count()

        if count:
            expired_qs.update(
                status=JarStatus.EXPIRED,
                updated_at=now,
            )
            logger.info(
                "update_expired_jar_statuses: marked %d jar(s) as expired",
                count,
            )

        return {"updated": count, "checked_at": now.isoformat()}

    except Exception as exc:
        logger.error("update_expired_jar_statuses failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# Fix missing import
from django.db import models
