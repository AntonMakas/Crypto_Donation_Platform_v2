"""
Signals for the jars app.

post_save on Donation → update jar.amount_raised_matic and re-evaluate status.
This keeps the off-chain database in sync without polling.
"""
import logging
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="donations.Donation")
def update_jar_on_donation_confirmed(sender, instance, created, **kwargs):
    """
    When a Donation is confirmed on-chain, update the parent Jar's
    raised amount and re-evaluate its status.

    Only fires when is_verified transitions to True.
    """
    from apps.donations.models import TxStatus

    # Only act on confirmed donations
    if instance.tx_status != TxStatus.CONFIRMED:
        return

    # Only run if `is_verified` just changed to True (not on every save)
    if not instance.is_verified:
        return

    jar = instance.jar

    # Recalculate total raised from confirmed donations
    from apps.donations.models import Donation
    from django.db.models import Sum

    total = Donation.objects.filter(
        jar=jar,
        tx_status=TxStatus.CONFIRMED,
        is_verified=True,
    ).aggregate(total=Sum("amount_matic"))["total"] or Decimal("0")

    jar.amount_raised_matic = total
    jar.donor_count = Donation.objects.filter(
        jar=jar,
        tx_status=TxStatus.CONFIRMED,
        is_verified=True,
    ).values("donor_wallet").distinct().count()

    jar.save(update_fields=["amount_raised_matic", "donor_count", "updated_at"])

    # Re-evaluate jar status
    changed = jar.sync_status()
    if changed:
        logger.info(
            "Jar #%s status updated to %s after donation #%s confirmed",
            jar.id,
            jar.status,
            instance.id,
        )
