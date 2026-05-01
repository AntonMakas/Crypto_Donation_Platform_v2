"""
Serializers for the donations app.

  DonationCreateSerializer — validates and records a new donation tx
  DonationListSerializer   — paginated list (jar detail, profile)
  DonationDetailSerializer — single donation with full blockchain data
"""
import re
from decimal import Decimal

from rest_framework import serializers
from web3 import Web3

from apps.donations.models import Donation, TxStatus


_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
_ETH_RE     = re.compile(r"^0x[0-9a-fA-F]{40}$")


# ─────────────────────────────────────────────────────────────────
#  DONATION CREATE
# ─────────────────────────────────────────────────────────────────

class DonationCreateSerializer(serializers.ModelSerializer):
    """
    POST /donations/

    Called immediately after the user submits the donate() transaction.
    The tx is stored as PENDING; Celery verifies it in the background.
    """
    jar_id       = serializers.IntegerField(write_only=True)
    donor_wallet = serializers.CharField(max_length=42)
    amount_wei   = serializers.CharField(
        required=False,
        allow_blank=True,
        default="0",
        help_text="Exact amount in wei as a string (prevents float precision loss).",
    )

    class Meta:
        model  = Donation
        fields = [
            "jar_id",
            "donor_wallet",
            "amount_matic",
            "amount_wei",
            "tx_hash",
            "message",
            "is_anonymous",
        ]

    def validate_donor_wallet(self, value: str) -> str:
        if not _ETH_RE.match(value):
            raise serializers.ValidationError("Invalid Ethereum address.")
        return Web3.to_checksum_address(value)

    def validate_tx_hash(self, value: str) -> str:
        if not _TX_HASH_RE.match(value):
            raise serializers.ValidationError(
                "Invalid transaction hash. Must be 0x + 64 hex characters."
            )
        if Donation.objects.filter(tx_hash=value).exists():
            raise serializers.ValidationError(
                "This transaction hash has already been recorded."
            )
        return value

    def validate_amount_matic(self, value: Decimal) -> Decimal:
        if value < Decimal("0.001"):
            raise serializers.ValidationError(
                "Minimum donation is 0.001 MATIC (contract minimum)."
            )
        if value > Decimal("1000000"):
            raise serializers.ValidationError("Donation exceeds maximum allowed amount.")
        return value

    def validate(self, attrs: dict) -> dict:
        from apps.jars.models import Jar, JarStatus
        from django.utils import timezone

        jar_id = attrs.pop("jar_id")

        try:
            jar = Jar.objects.get(pk=jar_id)
        except Jar.DoesNotExist:
            raise serializers.ValidationError({"jar_id": "Jar not found."})

        if jar.status != JarStatus.ACTIVE:
            raise serializers.ValidationError(
                {"jar_id": f"This jar is not accepting donations (status: {jar.status})."}
            )

        if timezone.now() >= jar.deadline:
            raise serializers.ValidationError(
                {"jar_id": "This jar's deadline has passed."}
            )

        # Prevent creator self-donation (mirrors contract check)
        donor_wallet = attrs.get("donor_wallet", "")
        if donor_wallet.lower() == jar.creator_wallet.lower():
            raise serializers.ValidationError(
                {"donor_wallet": "Jar creators cannot donate to their own jar."}
            )

        attrs["jar"] = jar
        return attrs

    def create(self, validated_data: dict) -> Donation:
        request = self.context.get("request")

        donation = Donation.objects.create(
            jar=validated_data["jar"],
            donor_wallet=validated_data["donor_wallet"],
            amount_matic=validated_data["amount_matic"],
            amount_wei=validated_data.get("amount_wei", "0"),
            tx_hash=validated_data["tx_hash"],
            tx_status=TxStatus.PENDING,
            message=validated_data.get("message", ""),
            is_anonymous=validated_data.get("is_anonymous", False),
        )

        # Queue background verification immediately
        from apps.blockchain.tasks import verify_single_transaction
        verify_single_transaction.apply_async(
            args=[donation.tx_hash],
            queue='celery',
            countdown=5,   # 5-second delay — let the tx propagate
        )

        return donation


# ─────────────────────────────────────────────────────────────────
#  DONATION LIST
# ─────────────────────────────────────────────────────────────────

class DonationListSerializer(serializers.ModelSerializer):
    """
    Paginated list item — used on jar detail page and profile page.
    Respects anonymity flag on donor_wallet.
    """
    donor_wallet = serializers.SerializerMethodField()
    explorer_url = serializers.ReadOnlyField()
    jar_title    = serializers.SerializerMethodField()
    jar_id       = serializers.IntegerField(source="jar.id", read_only=True)

    class Meta:
        model  = Donation
        fields = [
            "id",
            "jar_id", "jar_title",
            "donor_wallet",
            "amount_matic",
            "tx_hash", "tx_status",
            "is_verified", "is_anonymous",
            "message",
            "block_number", "confirmations",
            "explorer_url",
            "created_at", "verified_at",
        ]
        read_only_fields = fields

    def get_donor_wallet(self, obj) -> str:
        return obj.display_wallet

    def get_jar_title(self, obj) -> str:
        return obj.jar.title


# ─────────────────────────────────────────────────────────────────
#  DONATION DETAIL
# ─────────────────────────────────────────────────────────────────

class DonationDetailSerializer(DonationListSerializer):
    """Full donation record — includes all blockchain metadata."""
    class Meta(DonationListSerializer.Meta):
        fields = DonationListSerializer.Meta.fields + [
            "amount_wei",
            "block_timestamp",
            "gas_used", "gas_price_gwei",
            "verification_attempts", "last_verified_at",
            "updated_at",
        ]


# ─────────────────────────────────────────────────────────────────
#  DONATION STATS (for jar detail sidebar)
# ─────────────────────────────────────────────────────────────────

class DonationStatsSerializer(serializers.Serializer):
    """
    GET /jars/{id}/donation-stats/
    Aggregated donation statistics for a jar.
    """
    total_confirmed   = serializers.DecimalField(max_digits=20, decimal_places=6)
    total_pending     = serializers.DecimalField(max_digits=20, decimal_places=6)
    donor_count       = serializers.IntegerField()
    donation_count    = serializers.IntegerField()
    largest_donation  = serializers.DecimalField(max_digits=20, decimal_places=6)
    average_donation  = serializers.DecimalField(max_digits=20, decimal_places=6)
    latest_donation_at = serializers.DateTimeField(allow_null=True)
