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
