"""
Serializers for the blockchain app.

  TxVerifySerializer       — verify a single transaction hash
  TransactionLogSerializer — read-only audit log entry
  ContractEventSerializer  — decoded on-chain event
  PlatformStatsSerializer  — aggregate platform statistics
"""
import re
from rest_framework import serializers
from .models import TransactionLog, ContractEvent

_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")


# ─────────────────────────────────────────────────────────────────
#  TX VERIFY REQUEST
# ─────────────────────────────────────────────────────────────────

class TxVerifyRequestSerializer(serializers.Serializer):
    """
    POST /blockchain/verify/
    Manually trigger verification for a tx hash.
    """
    tx_hash = serializers.CharField(max_length=66)

    def validate_tx_hash(self, value: str) -> str:
        if not _TX_HASH_RE.match(value):
            raise serializers.ValidationError(
                "Invalid transaction hash. Expected 0x + 64 hex characters."
            )
        return value


# ─────────────────────────────────────────────────────────────────
#  TX STATUS RESPONSE
# ─────────────────────────────────────────────────────────────────

class TxStatusSerializer(serializers.Serializer):
    """
    GET /blockchain/tx/{tx_hash}/
    Returns current verification status of a transaction.
    """
    tx_hash         = serializers.CharField()
    status          = serializers.CharField()
    is_verified     = serializers.BooleanField()
    block_number    = serializers.IntegerField(allow_null=True)
    confirmations   = serializers.IntegerField()
    gas_used        = serializers.IntegerField(allow_null=True)
    gas_price_gwei  = serializers.DecimalField(
        max_digits=20, decimal_places=9, allow_null=True
    )
    verified_at     = serializers.DateTimeField(allow_null=True)
    explorer_url    = serializers.CharField()
    source          = serializers.CharField(
        help_text="'db' if from database, 'rpc' if freshly fetched from node."
    )


# ─────────────────────────────────────────────────────────────────
#  TRANSACTION LOG
# ─────────────────────────────────────────────────────────────────

class TransactionLogSerializer(serializers.ModelSerializer):
    explorer_url = serializers.ReadOnlyField()

    class Meta:
        model  = TransactionLog
        fields = [
            "id", "tx_hash", "tx_type",
            "from_wallet", "to_wallet",
            "chain_id", "block_number", "block_timestamp",
            "value_matic", "gas_used", "gas_price_gwei",
            "status", "confirmations",
            "jar_id_ref", "donation_id_ref",
            "explorer_url",
            "created_at", "confirmed_at",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────────────────────────────
#  CONTRACT EVENTS
# ─────────────────────────────────────────────────────────────────

class ContractEventSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ContractEvent
        fields = [
            "id", "tx_hash", "event_type",
            "log_index", "block_number", "block_timestamp",
            "event_data", "chain_jar_id", "emitter_wallet",
            "created_at",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────────────────────────────
#  PLATFORM STATS
# ─────────────────────────────────────────────────────────────────

class PlatformStatsSerializer(serializers.Serializer):
    """
    GET /blockchain/stats/
    Aggregate platform-wide statistics — shown on the landing page.
    """
    total_jars          = serializers.IntegerField()
    active_jars         = serializers.IntegerField()
    completed_jars      = serializers.IntegerField()
    total_raised_matic  = serializers.DecimalField(max_digits=20, decimal_places=4)
    total_donors        = serializers.IntegerField()
    total_donations     = serializers.IntegerField()
    verified_donations  = serializers.IntegerField()
    # Recent activity
    donations_last_24h  = serializers.IntegerField()
    raised_last_24h     = serializers.DecimalField(max_digits=20, decimal_places=4)
