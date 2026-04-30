"""
Jar model — the core entity in JarFund.

A Jar represents a single fundraising campaign. It is created by a user
(identified by their wallet address), deployed on-chain, and funded by
donors who send MATIC to the smart contract.

Database table:  jars_jar
"""
from decimal import Decimal
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from .validators import validate_wallet_address, validate_future_deadline


class JarCategory(models.TextChoices):
    HUMANITARIAN  = "humanitarian",  "Humanitarian"
    TECHNOLOGY    = "technology",    "Technology"
    EDUCATION     = "education",     "Education"
    ENVIRONMENT   = "environment",   "Environment"
    HEALTHCARE    = "healthcare",    "Healthcare"
    GAMING        = "gaming",        "Gaming"
    ARTS          = "arts",          "Arts & Culture"
    COMMUNITY     = "community",     "Community"
    RESEARCH      = "research",      "Research"
    OTHER         = "other",         "Other"


class JarStatus(models.TextChoices):
    ACTIVE    = "active",     "Active"      # Accepting donations
    COMPLETED = "completed",  "Completed"   # Target reached
    EXPIRED   = "expired",    "Expired"     # Deadline passed, target not met
    WITHDRAWN = "withdrawn",  "Withdrawn"   # Funds claimed by creator


class Jar(models.Model):
    """
    A fundraising campaign ("Jar") created by a wallet user.

    Fields mirror the on-chain Jar struct, with additional metadata
    stored off-chain in PostgreSQL for fast querying and display.
    """

    # ── Identity ──────────────────────────────────────────────────
    id = models.BigAutoField(primary_key=True)

    # The on-chain jar ID returned by JarFund.createJar()
    # Null until the tx is confirmed on-chain
    chain_jar_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="The uint256 jar ID from the smart contract (set after on-chain confirmation).",
    )

    # ── Creator ───────────────────────────────────────────────────
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,          # Never delete jars when user is removed
        related_name="jars",
        help_text="The authenticated user who created this jar.",
    )

    # Denormalized for fast filtering without JOIN
    creator_wallet = models.CharField(
        max_length=42,
        db_index=True,
        validators=[validate_wallet_address],
        help_text="Checksum Ethereum address of the creator (denormalized from creator.wallet_address).",
    )

    # ── Campaign Content ──────────────────────────────────────────
    title = models.CharField(
        max_length=120,
        db_index=True,
        help_text="Short name of the fundraiser (max 120 chars, matches contract limit).",
    )

    description = models.TextField(
        max_length=1000,
        help_text="Full description of the fundraiser (max 1000 chars).",
    )

    category = models.CharField(
        max_length=20,
        choices=JarCategory.choices,
        default=JarCategory.OTHER,
        db_index=True,
    )

    cover_emoji = models.CharField(
        max_length=8,
        default="🫙",
        help_text="Single emoji used as the jar's cover icon.",
    )

    cover_image_url = models.URLField(
        blank=True,
        default="",
        help_text="Optional cover image URL.",
    )

    # ── Financial ─────────────────────────────────────────────────
    target_amount_matic = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Fundraising target in MATIC.",
    )

    amount_raised_matic = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=Decimal("0.000000"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Total MATIC raised so far (synced from chain).",
    )

    # ── Timeline ──────────────────────────────────────────────────
    deadline = models.DateTimeField(
        db_index=True,
        validators=[validate_future_deadline],
        help_text="Deadline after which the creator can withdraw funds.",
    )

    # ── Status ────────────────────────────────────────────────────
    status = models.CharField(
        max_length=12,
        choices=JarStatus.choices,
        default=JarStatus.ACTIVE,
        db_index=True,
    )

    # ── Blockchain metadata ───────────────────────────────────────
    # Transaction hash of the createJar() call
    creation_tx_hash = models.CharField(
        max_length=66,
        blank=True,
        default="",
        db_index=True,
        help_text="Tx hash of the createJar() transaction.",
    )

    is_verified_on_chain = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True once the creation tx has been confirmed on-chain.",
    )

    # ── Stats (cached — refreshed by Celery tasks) ────────────────
    donor_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of unique donors (cached from chain/donations table).",
    )

    # ── Timestamps ────────────────────────────────────────────────
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # Withdrawal timestamp
    withdrawn_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the creator withdrew the funds.",
    )
    withdrawal_tx_hash = models.CharField(
        max_length=66,
        blank=True,
        default="",
        help_text="Tx hash of the withdraw() call.",
    )

    class Meta:
        db_table    = "jars_jar"
        ordering    = ["-created_at"]
        verbose_name        = "Jar"
        verbose_name_plural = "Jars"
        indexes = [
            models.Index(fields=["status", "deadline"],      name="idx_jar_status_deadline"),
            models.Index(fields=["creator_wallet", "status"],name="idx_jar_creator_status"),
            models.Index(fields=["category", "status"],      name="idx_jar_category_status"),
            models.Index(fields=["is_verified_on_chain"],    name="idx_jar_verified"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_raised_matic__gte=0),
                name="chk_jar_raised_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(target_amount_matic__gte=Decimal("0.01")),
                name="chk_jar_target_min",
            ),
        ]

    # ── String representation ──────────────────────────────────────
    def __str__(self):
        return f"[{self.id}] {self.title} ({self.status}) — {self.creator_wallet[:8]}…"

    # ── Computed properties ───────────────────────────────────────
    @property
    def progress_percentage(self) -> float:
        """Funding progress as a percentage (0.0 – 100.0)."""
        if not self.target_amount_matic or self.target_amount_matic == 0:
            return 0.0
        pct = float(self.amount_raised_matic / self.target_amount_matic * 100)
        return min(pct, 100.0)

    @property
    def is_active(self) -> bool:
        return self.status == JarStatus.ACTIVE

    @property
    def is_deadline_passed(self) -> bool:
        return timezone.now() >= self.deadline

    @property
    def can_withdraw(self) -> bool:
        """True if the creator is eligible to call withdraw() on-chain."""
        if self.status == JarStatus.WITHDRAWN:
            return False
        if self.amount_raised_matic <= 0:
            return False
        return self.is_deadline_passed or (self.amount_raised_matic >= self.target_amount_matic)

    @property
    def time_remaining_seconds(self) -> int:
        """Seconds until deadline (0 if already passed)."""
        delta = self.deadline - timezone.now()
        return max(0, int(delta.total_seconds()))

    @property
    def explorer_url(self) -> str:
        """PolygonScan URL for the creation transaction."""
        if not self.creation_tx_hash:
            return ""
        base = settings.BLOCKCHAIN.get("EXPLORER_URL", "https://amoy.polygonscan.com")
        return f"{base}/tx/{self.creation_tx_hash}"

    # ── Business logic helpers ────────────────────────────────────
    def sync_status(self) -> bool:
        """
        Re-evaluate and update the jar status based on current state.
        Returns True if the status changed.

        Called by Celery periodic task and after each donation.
        """
        old_status = self.status

        if self.status == JarStatus.WITHDRAWN:
            return False  # Terminal state — nothing to sync

        if self.amount_raised_matic >= self.target_amount_matic:
            self.status = JarStatus.COMPLETED
        elif self.is_deadline_passed:
            self.status = JarStatus.EXPIRED
        else:
            self.status = JarStatus.ACTIVE

        if self.status != old_status:
            self.save(update_fields=["status", "updated_at"])
            return True
        return False

    def refresh_cached_totals(self, *, save: bool = True) -> bool:
        """
        Recalculate cached raised amount and donor count from confirmed donations.
        Returns True if any cached value changed.
        """
        from django.db.models import Sum
        from apps.donations.models import Donation, TxStatus

        confirmed = Donation.objects.filter(
            jar=self,
            tx_status=TxStatus.CONFIRMED,
            is_verified=True,
        )

        total = confirmed.aggregate(total=Sum("amount_matic"))["total"] or Decimal("0")
        donors = confirmed.values("donor_wallet").distinct().count()

        changed = False
        update_fields: list[str] = []

        if self.amount_raised_matic != total:
            self.amount_raised_matic = total
            update_fields.append("amount_raised_matic")
            changed = True

        if self.donor_count != donors:
            self.donor_count = donors
            update_fields.append("donor_count")
            changed = True

        if changed and save:
            self.save(update_fields=[*update_fields, "updated_at"])

        return changed

    def save(self, *args, **kwargs):
        # Always denormalize creator_wallet from the FK
        if self.creator_id and not self.creator_wallet:
            self.creator_wallet = self.creator.wallet_address
        super().save(*args, **kwargs)
