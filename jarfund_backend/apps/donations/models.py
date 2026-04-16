"""
Donation model — records every donation made to a Jar.

Each Donation corresponds to one donate() transaction on-chain.
The backend stores the tx hash immediately (status: PENDING) and a
Celery task verifies it against the RPC node within seconds.

Database table:  donations_donation
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.jars.validators import (
    validate_wallet_address,
    validate_tx_hash,
    validate_min_donation,
)


class TxStatus(models.TextChoices):
    PENDING   = "pending",   "Pending"    # Submitted, not yet confirmed
    CONFIRMED = "confirmed", "Confirmed"  # On-chain, required confirmations met
    FAILED    = "failed",    "Failed"     # Reverted or dropped
    REPLACED  = "replaced",  "Replaced"  # Replaced by a higher-gas tx (EIP-1559)


class Donation(models.Model):
    """
    A single MATIC donation to a fundraising Jar.

    Created by the frontend immediately after the user submits the
    MetaMask transaction. The tx_hash is stored straight away with
    status=PENDING. A Celery worker then polls the RPC node and
    updates the record to CONFIRMED or FAILED.
    """

    # ── Identity ──────────────────────────────────────────────────
    id = models.BigAutoField(primary_key=True)

    # ── Relations ─────────────────────────────────────────────────
    jar = models.ForeignKey(
        "jars.Jar",
        on_delete=models.PROTECT,
        related_name="donations",
        db_index=True,
    )

    # The authenticated user who donated (null if donor is not registered)
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations_made",
        help_text="Linked user account (null if donor wallet not registered).",
    )

    # ── Wallet ────────────────────────────────────────────────────
    donor_wallet = models.CharField(
        max_length=42,
        db_index=True,
        validators=[validate_wallet_address],
        help_text="Checksum Ethereum address of the donor.",
    )

    # ── Amount ────────────────────────────────────────────────────
    amount_matic = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal("0.001")),
            validate_min_donation,
        ],
        help_text="Donation amount in MATIC.",
    )

    amount_wei = models.CharField(
        max_length=78,           # Max uint256 = 78 digits
        default="0",
        help_text="Exact donation amount in wei (string to avoid float precision loss).",
    )

    # ── Blockchain ────────────────────────────────────────────────
    tx_hash = models.CharField(
        max_length=66,
        unique=True,
        db_index=True,
        validators=[validate_tx_hash],
        help_text="Ethereum transaction hash of the donate() call.",
    )

    tx_status = models.CharField(
        max_length=10,
        choices=TxStatus.choices,
        default=TxStatus.PENDING,
        db_index=True,
    )

    block_number = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Block number in which the tx was mined.",
    )

    block_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Block timestamp from the chain (may differ slightly from created_at).",
    )

    gas_used = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Gas consumed by the donate() call.",
    )

    gas_price_gwei = models.DecimalField(
        max_digits=20,
        decimal_places=9,
        null=True,
        blank=True,
        help_text="Gas price in gwei.",
    )

    confirmations = models.PositiveIntegerField(
        default=0,
        help_text="Number of block confirmations at last verification check.",
    )

    # ── Verification ──────────────────────────────────────────────
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True once the required number of block confirmations is reached.",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the transaction was confirmed and verified.",
    )

    # Number of verification check attempts (for retry logic)
    verification_attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text="How many times the verification Celery task has polled this tx.",
    )

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the Celery worker checked this transaction.",
    )

    # ── Message ───────────────────────────────────────────────────
    message = models.CharField(
        max_length=280,
        blank=True,
        default="",
        help_text="Optional donor message (Twitter/X-style, 280 chars).",
    )

    is_anonymous = models.BooleanField(
        default=False,
        help_text="If True, donor wallet is hidden from public API responses.",
    )

    # ── Timestamps ────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "donations_donation"
        ordering = ["-created_at"]
        verbose_name        = "Donation"
        verbose_name_plural = "Donations"
        indexes = [
            models.Index(fields=["tx_status", "is_verified"],      name="idx_donation_status_verified"),
            models.Index(fields=["donor_wallet", "tx_status"],     name="idx_donation_donor_status"),
            models.Index(fields=["jar", "tx_status"],              name="idx_donation_jar_status"),
            models.Index(fields=["tx_status", "verification_attempts"], name="idx_donation_pending_attempts"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_matic__gte=Decimal("0.001")),
                name="chk_donation_min_amount",
            ),
        ]

    def __str__(self):
        return (
            f"Donation #{self.id} — {self.amount_matic} MATIC "
            f"to Jar #{self.jar_id} ({self.tx_status})"
        )

    # ── Properties ────────────────────────────────────────────────
    @property
    def is_pending(self) -> bool:
        return self.tx_status == TxStatus.PENDING

    @property
    def is_confirmed(self) -> bool:
        return self.tx_status == TxStatus.CONFIRMED

    @property
    def explorer_url(self) -> str:
        """Direct PolygonScan link for the transaction."""
        base = settings.BLOCKCHAIN.get("EXPLORER_URL", "https://amoy.polygonscan.com")
        return f"{base}/tx/{self.tx_hash}"

    @property
    def display_wallet(self) -> str:
        """Returns the wallet address unless the donor chose anonymity."""
        if self.is_anonymous:
            return "Anonymous"
        return self.donor_wallet

    # ── Business logic ────────────────────────────────────────────
    def mark_confirmed(
        self,
        block_number: int,
        block_timestamp,
        gas_used: int,
        gas_price_gwei: Decimal,
        confirmations: int,
    ) -> None:
        """
        Mark this donation as confirmed on-chain.
        Called by the Celery verification task.
        """
        self.tx_status      = TxStatus.CONFIRMED
        self.is_verified    = True
        self.verified_at    = timezone.now()
        self.block_number   = block_number
        self.block_timestamp = block_timestamp
        self.gas_used       = gas_used
        self.gas_price_gwei = gas_price_gwei
        self.confirmations  = confirmations
        self.last_verified_at = timezone.now()
        self.save(update_fields=[
            "tx_status", "is_verified", "verified_at",
            "block_number", "block_timestamp", "gas_used",
            "gas_price_gwei", "confirmations", "last_verified_at",
            "updated_at",
        ])

    def mark_failed(self) -> None:
        """Mark the transaction as failed/reverted."""
        self.tx_status = TxStatus.FAILED
        self.last_verified_at = timezone.now()
        self.save(update_fields=["tx_status", "last_verified_at", "updated_at"])

    def increment_verification_attempt(self) -> None:
        """Bump the counter every time the Celery task polls this tx."""
        self.verification_attempts += 1
        self.last_verified_at = timezone.now()
        self.save(update_fields=["verification_attempts", "last_verified_at"])
