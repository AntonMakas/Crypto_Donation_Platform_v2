"""
Custom User model for JarFund.

Authentication is wallet-based: users sign a nonce with MetaMask,
the backend verifies the signature and issues a JWT.
The Django User model stores the wallet address as the primary identifier.

Fields:
  - wallet_address  : Ethereum address (primary identifier, unique)
  - username        : Optional display name (can be set later)
  - nonce           : Random challenge for signature-based auth
  - is_verified     : True once wallet ownership has been proven
  - created_at      : Registration timestamp
"""
import uuid
import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extended Django user with Ethereum wallet authentication.

    We keep AbstractUser (not AbstractBaseUser) so the Django admin
    and DRF's built-in auth still work with minimal friction.
    The wallet_address is made unique and is used as the primary
    login credential instead of username/password.
    """

    # Override username to be optional (wallet is the identifier)
    username = models.CharField(
        max_length=80,
        unique=False,
        blank=True,
        default="",
        help_text="Optional display name.",
    )

    # ── Wallet ──
    wallet_address = models.CharField(
        max_length=42,
        unique=True,
        db_index=True,
        help_text="Ethereum address in checksum format (0x…).",
    )

    # ── Auth nonce (rotated after each successful login) ──
    nonce = models.CharField(
        max_length=64,
        default=secrets.token_hex,
        help_text=(
            "One-time challenge string the user must sign with their wallet. "
            "Rotated after every successful authentication."
        ),
    )

    # ── Verification status ──
    is_verified = models.BooleanField(
        default=False,
        help_text="True once wallet ownership has been proven via signature.",
    )

    # ── Profile ──
    bio = models.TextField(blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")

    # ── Timestamps ──
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
        """Returns a shortened wallet address for display: 0x1234…abcd."""
        if not self.wallet_address:
            return ""
        addr = self.wallet_address
        return f"{addr[:6]}…{addr[-4:]}"

    def rotate_nonce(self) -> str:
        """Generate and save a new nonce. Call this after successful auth."""
        self.nonce = secrets.token_hex(32)
        self.save(update_fields=["nonce"])
        return self.nonce

    @property
    def display_name(self) -> str:
        """Best available name for the user."""
        return self.username or self.get_short_wallet()

    @property
    def total_donated(self):
        """Sum of all confirmed donations made by this user."""
        from apps.donations.models import Donation
        from django.db.models import Sum
        result = Donation.objects.filter(
            donor_wallet__iexact=self.wallet_address,
            tx_status=Donation.TxStatus.CONFIRMED,
        ).aggregate(total=Sum("amount_matic"))
        return result["total"] or 0

    @property
    def total_raised(self):
        """Sum of all funds raised across jars created by this user."""
        from django.db.models import Sum
        result = self.jars.aggregate(total=Sum("amount_raised_matic"))
        return result["total"] or 0
