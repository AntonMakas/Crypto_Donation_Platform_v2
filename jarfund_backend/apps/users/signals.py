"""
Signals for the users app.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def log_new_user(sender, instance, created, **kwargs):
    """Log when a new user registers via wallet connection."""
    if created:
        logger.info(
            "New user registered: wallet=%s",
            instance.wallet_address,
        )
