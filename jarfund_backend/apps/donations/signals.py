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
    When a donation is saved as CONFIRMED and verified, refresh the jar's
    cached totals and sync its status. This is a safety net — the processor
    calls these methods directly, but this signal ensures the jar is always
    up to date even if the donation is confirmed via other code paths
    (e.g. Django Admin).
    """
    from apps.donations.models import TxStatus

    if created:
        return  # New donations are always PENDING — nothing to refresh yet

    if instance.tx_status != TxStatus.CONFIRMED or not instance.is_verified:
        return  # Only act on fully confirmed+verified donations

    try:
        jar = instance.jar
        jar.refresh_cached_totals()
        jar.sync_status()
        logger.info(
            "refresh_jar_on_donation_confirmed: refreshed jar #%s totals "
            "after donation #%s confirmed",
            jar.id,
            instance.id,
        )
    except Exception:
        logger.exception(
            "refresh_jar_on_donation_confirmed: failed to refresh jar for donation #%s",
            instance.id,
        )
