"""
Signals for the donations app.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="donations.Donation")
def link_donor_user_account(sender, instance, created, **kwargs):
    """
    When a new donation is created, try to link it to a registered
    user account (by wallet address). This is best-effort — many donors
    may not have registered accounts.
    """
    if not created:
        return
    if instance.donor_id:
        return  # Already linked

    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(wallet_address__iexact=instance.donor_wallet)
        instance.donor = user
        instance.save(update_fields=["donor"])
        logger.debug(
            "Linked donation #%s to user %s",
            instance.id,
            user.wallet_address,
        )
    except User.DoesNotExist:
        pass  # Donor hasn't registered — that's fine


@receiver(post_save, sender="donations.Donation")
def refresh_jar_on_donation_confirmed(sender, instance, created, **kwargs):
    """
    Safety-net signal handler: whenever a Donation is saved in a
    CONFIRMED + is_verified=True state, refresh the parent Jar's cached
    totals and re-evaluate its status.

    This fires unconditionally for any save that lands in the confirmed+verified
    state, making it robust against all confirmation paths (Celery worker,
    Django Admin, management commands, etc.).  The underlying helpers
    (refresh_cached_totals / sync_status) are idempotent, so duplicate calls
    are harmless.

    Note: the processor already calls jar.refresh_cached_totals() and
    jar.sync_status() explicitly after mark_confirmed().  This handler acts
    as a belt-and-suspenders guarantee for any path that bypasses the
    processor directly.
    """
    from apps.donations.models import TxStatus

    # Only act on confirmed, verified donations.
    if instance.tx_status != TxStatus.CONFIRMED or not instance.is_verified:
        return

    # Skip brand-new records — a donation is never created already-verified.
    if created:
        return

    jar = instance.jar

    changed = jar.refresh_cached_totals()
    status_changed = jar.sync_status()

    if changed or status_changed:
        logger.info(
            "Jar #%s refreshed after donation #%s confirmed — "
            "raised=%.6f, donors=%d, status=%s",
            jar.id,
            instance.id,
            jar.amount_raised_matic,
            jar.donor_count,
            jar.status,
        )
    else:
        logger.debug(
            "Jar #%s totals unchanged after donation #%s confirmed",
            jar.id,
            instance.id,
        )
