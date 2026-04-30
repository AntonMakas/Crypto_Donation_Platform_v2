"""
Signals for the donations app.
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Tracks Donation PKs whose is_verified was False immediately before the
# current save.  Populated by _capture_pre_verification_state (pre_save) and
# consumed by refresh_jar_on_donation_verified (post_save).
#
# A module-level set is safe because Django signals are dispatched
# synchronously within a single thread (request or Celery task).
_pending_verification: set = set()


@receiver(pre_save, sender="donations.Donation")
def _capture_pre_verification_state(sender, instance, **kwargs):
    """
    Before a Donation is written to the DB, record whether is_verified was
    False so that the post_save handler can detect the False → True transition.

    We must read the current DB value here (before the write) because by the
    time post_save fires the row already has the new value.
    """
    if instance.pk is None:
        # Brand-new record — no previous state to capture.
        return

    try:
        currently_unverified = sender.objects.filter(
            pk=instance.pk, is_verified=False
        ).exists()
    except Exception:
        return

    if currently_unverified:
        _pending_verification.add(instance.pk)
    else:
        _pending_verification.discard(instance.pk)


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
def refresh_jar_on_donation_verified(sender, instance, created, **kwargs):
    """
    When a Donation is verified by the backend worker (is_verified flips to
    True), refresh the parent Jar's cached totals and re-evaluate its status.

    This is the authoritative handler for keeping jar.amount_raised_matic,
    jar.donor_count, and jar.status in sync after the Celery verification
    task confirms a transaction on-chain.

    Transition detection is a two-step process:
      1. pre_save (_capture_pre_verification_state) records which PKs had
         is_verified=False before the write.
      2. post_save (this handler) checks that set and only proceeds when the
         transition False → True actually occurred.
    """
    from apps.donations.models import TxStatus

    # Only act on confirmed, verified donations.
    if instance.tx_status != TxStatus.CONFIRMED or not instance.is_verified:
        return

    # Skip brand-new records — a donation is never created already-verified.
    if created:
        return

    # Only proceed if is_verified just flipped from False to True.
    if instance.pk not in _pending_verification:
        return

    # Consume the marker now that we've acted on the transition.
    _pending_verification.discard(instance.pk)

    jar = instance.jar

    changed = jar.refresh_cached_totals()
    status_changed = jar.sync_status()

    if changed or status_changed:
        logger.info(
            "Jar #%s refreshed after donation #%s verified — "
            "raised=%.6f, donors=%d, status=%s",
            jar.id,
            instance.id,
            jar.amount_raised_matic,
            jar.donor_count,
            jar.status,
        )
    else:
        logger.debug(
            "Jar #%s totals unchanged after donation #%s verified",
            jar.id,
            instance.id,
        )
