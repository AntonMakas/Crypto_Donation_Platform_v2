"""
Blockchain models — low-level on-chain record keeping.

TransactionLog  : Immutable audit log of every tx we've ever processed.
ContractEvent   : Decoded smart contract event logs (JarCreated,
                  DonationReceived, FundsWithdrawn, JarStatusChanged).

These tables are append-only. Nothing is ever deleted from them —
they form the immutable audit trail for the platform.

Database tables:
  blockchain_transactionlog
  blockchain_contractevent
"""
from django.db import models

from apps.jars.validators import validate_wallet_address, validate_tx_hash


# ─────────────────────────────────────────────────────────────────
#  TRANSACTION LOG
# ─────────────────────────────────────────────────────────────────

class TxType(models.TextChoices):
    CREATE_JAR  = "create_jar",  "Create Jar"
    DONATE      = "donate",      "Donate"
    WITHDRAW    = "withdraw",    "Withdraw"
    OTHER       = "other",       "Other"


class TxLogStatus(models.TextChoices):
    PENDING   = "pending",   "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED    = "failed",    "Failed"


class TransactionLog(models.Model):
    """
    Immutable audit log of every Ethereum transaction we process.

    Created as soon as we receive a tx hash from the frontend.
    Updated by the Celery verification task.

    Never deleted — forms the audit trail.
    """

    # ── Identity ──────────────────────────────────────────────────
    id = models.BigAutoField(primary_key=True)

    tx_hash = models.CharField(
        max_length=66,
        unique=True,
        db_index=True,
        validators=[validate_tx_hash],
        help_text="Ethereum transaction hash.",
    )

    tx_type = models.CharField(
        max_length=12,
        choices=TxType.choices,
        db_index=True,
    )

    # ── Parties ───────────────────────────────────────────────────
    from_wallet = models.CharField(
        max_length=42,
        db_index=True,
        validators=[validate_wallet_address],
        help_text="Address that initiated the transaction (msg.sender).",
    )

    to_wallet = models.CharField(
        max_length=42,
        blank=True,
        default="",
        help_text="Destination address (contract address for contract calls).",
    )

    # ── Chain data ────────────────────────────────────────────────
    chain_id = models.PositiveIntegerField(
        default=80002,
        help_text="Chain ID (Amoy=80002, Polygon=137, Hardhat=31337).",
    )

    block_number = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    block_hash = models.CharField(
        max_length=66,
        blank=True,
        default="",
    )

    block_timestamp = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ── Value ─────────────────────────────────────────────────────
    value_wei = models.CharField(
        max_length=78,
        default="0",
        help_text="Transaction value in wei (string for precision).",
    )

    value_matic = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0,
        help_text="Transaction value in MATIC (human-readable).",
    )

    # ── Gas ───────────────────────────────────────────────────────
    gas_used      = models.PositiveBigIntegerField(null=True, blank=True)
    gas_limit     = models.PositiveBigIntegerField(null=True, blank=True)
    gas_price_wei = models.CharField(max_length=30, blank=True, default="")
    gas_price_gwei = models.DecimalField(
        max_digits=20, decimal_places=9, null=True, blank=True,
    )

    # ── Status ────────────────────────────────────────────────────
    status = models.CharField(
        max_length=10,
        choices=TxLogStatus.choices,
        default=TxLogStatus.PENDING,
        db_index=True,
    )

    confirmations = models.PositiveIntegerField(default=0)

    # ── Context (polymorphic FK via generic fields) ───────────────
    # We store these as nullable FKs for flexibility
    jar_id_ref = models.PositiveBigIntegerField(
        null=True, blank=True,
        help_text="ID of the related Jar record, if applicable.",
    )
    donation_id_ref = models.PositiveBigIntegerField(
        null=True, blank=True,
        help_text="ID of the related Donation record, if applicable.",
    )

    # Raw transaction receipt stored as JSON for debugging
    raw_receipt = models.JSONField(
        null=True,
        blank=True,
        help_text="Full JSON receipt from web3.py (for debugging/auditing).",
    )

    # ── Timestamps ────────────────────────────────────────────────
    created_at    = models.DateTimeField(auto_now_add=True, db_index=True)
    confirmed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "blockchain_transactionlog"
        ordering = ["-created_at"]
        verbose_name        = "Transaction Log"
        verbose_name_plural = "Transaction Logs"
        indexes = [
            models.Index(fields=["status", "tx_type"],        name="idx_txlog_status_type"),
            models.Index(fields=["from_wallet", "tx_type"],   name="idx_txlog_wallet_type"),
            models.Index(fields=["block_number"],              name="idx_txlog_block"),
        ]

    def __str__(self):
        return f"[{self.tx_type}] {self.tx_hash[:12]}… ({self.status})"

    @property
    def explorer_url(self) -> str:
        from django.conf import settings
        base = settings.BLOCKCHAIN.get("EXPLORER_URL", "https://amoy.polygonscan.com")
        return f"{base}/tx/{self.tx_hash}"


# ─────────────────────────────────────────────────────────────────
#  CONTRACT EVENTS
# ─────────────────────────────────────────────────────────────────

class EventType(models.TextChoices):
    JAR_CREATED        = "JarCreated",        "Jar Created"
    DONATION_RECEIVED  = "DonationReceived",  "Donation Received"
    FUNDS_WITHDRAWN    = "FundsWithdrawn",    "Funds Withdrawn"
    JAR_STATUS_CHANGED = "JarStatusChanged",  "Jar Status Changed"
    PLATFORM_FEE_UPDATED = "PlatformFeeUpdated", "Platform Fee Updated"


class ContractEvent(models.Model):
    """
    Decoded event logs emitted by the JarFund smart contract.

    Populated by the Celery worker after a transaction is confirmed.
    Provides a queryable history of everything that happened on-chain.
    """

    # ── Identity ──────────────────────────────────────────────────
    id = models.BigAutoField(primary_key=True)

    # The transaction this event belongs to
    tx_log = models.ForeignKey(
        TransactionLog,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )

    tx_hash = models.CharField(
        max_length=66,
        db_index=True,
        validators=[validate_tx_hash],
    )

    # ── Event metadata ────────────────────────────────────────────
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        db_index=True,
    )

    # Log index within the block (for uniqueness)
    log_index = models.PositiveIntegerField(default=0)

    block_number = models.PositiveBigIntegerField(db_index=True)

    block_timestamp = models.DateTimeField(null=True, blank=True)

    # ── Decoded event arguments (from ABI) ────────────────────────
    # Stored as JSON — structure depends on event_type
    # e.g. JarCreated:       { jarId, creator, title, targetAmount, deadline }
    # e.g. DonationReceived: { jarId, donor, amount, newTotal, timestamp }
    # e.g. FundsWithdrawn:   { jarId, creator, amount, timestamp }
    event_data = models.JSONField(
        default=dict,
        help_text="Decoded event arguments from ABI.",
    )

    # ── Relations (denormalized for fast lookup) ──────────────────
    chain_jar_id = models.PositiveBigIntegerField(
        null=True, blank=True, db_index=True,
        help_text="on-chain jar ID from event args (if applicable).",
    )

    emitter_wallet = models.CharField(
        max_length=42,
        blank=True,
        default="",
        db_index=True,
        help_text="The wallet address that triggered this event (indexed arg).",
    )

    # ── Timestamp ─────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "blockchain_contractevent"
        ordering = ["-block_number", "log_index"]
        verbose_name        = "Contract Event"
        verbose_name_plural = "Contract Events"
        unique_together = [["tx_hash", "log_index"]]  # One event per log slot
        indexes = [
            models.Index(fields=["event_type", "block_number"], name="idx_event_type_block"),
            models.Index(fields=["chain_jar_id", "event_type"], name="idx_event_jar_type"),
            models.Index(fields=["emitter_wallet"],             name="idx_event_wallet"),
        ]

    def __str__(self):
        return f"{self.event_type} — tx {self.tx_hash[:12]}… block #{self.block_number}"
