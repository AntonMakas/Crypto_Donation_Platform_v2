import uuid
import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Override username to be optional (wallet is the identifier)
    username = models.CharField(
        max_length=80,
        unique=False,
        blank=True,
        default="",
        help_text="Optional display name.",
    )

    #Wallet
    wallet_address = models.CharField(
        max_length=42,
        unique=True,
        db_index=True,
        help_text="Ethereum address in checksum format (0x…).",
    )

    # Auth nonce (rotated after each successful login)
    nonce = models.CharField(
        max_length=64,
        default=secrets.token_hex,
        help_text=(
            "One-time challenge string the user must sign with their wallet. "
            "Rotated after every successful authentication."
        ),
    )

    # Verification status
    is_verified = models.BooleanField(
        default=False,
        help_text="True once wallet ownership has been proven via signature.",
    )

    # Profile 
    bio = models.TextField(blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")

    # Timestamps 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    # Use wallet_address as the unique identifier for auth
    USERNAME_FIELD  = "wallet_address"
    REQUIRED_FIELDS = []   # No email/username required

    class Meta:
        verbose_name        = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        display = self.username or self.get_short_wallet()
        return f"{display} ({self.wallet_address})"

    def get_short_wallet(self) -> str:
        if not self.wallet_address:
            return ""
        addr = self.wallet_address
        return f"{addr[:6]}…{addr[-4:]}"

    def rotate_nonce(self) -> str:
        self.nonce = secrets.token_hex(32)
        self.save(update_fields=["nonce"])
        return self.nonce

    @property
    def display_name(self) -> str:
        return self.username or self.get_short_wallet()

    @property
    def total_donated(self):
        from apps.donations.models import Donation
        from django.db.models import Sum
        result = Donation.objects.filter(
            donor_wallet__iexact=self.wallet_address,
            tx_status=Donation.TxStatus.CONFIRMED,
        ).aggregate(total=Sum("amount_matic"))
        return result["total"] or 0

    @property
    def total_raised(self):
        from django.db.models import Sum
        result = self.jars.aggregate(total=Sum("amount_raised_matic"))
        return result["total"] or 0
