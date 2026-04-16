"""
Serializers for the jars app.

  JarListSerializer   — lightweight, used in grids (no donation list)
  JarDetailSerializer — full jar with recent donations embedded
  JarCreateSerializer — validates and creates a new jar
  JarUpdateSerializer — PATCH for creator (metadata only, not financials)
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers
from web3 import Web3

from apps.jars.models import Jar, JarStatus, JarCategory
from apps.jars.validators import validate_wallet_address


# ─────────────────────────────────────────────────────────────────
#  JAR LIST (lightweight — for grid / explore page)
# ─────────────────────────────────────────────────────────────────

class JarListSerializer(serializers.ModelSerializer):
    progress_percentage   = serializers.ReadOnlyField()
    time_remaining_seconds = serializers.ReadOnlyField()
    can_withdraw          = serializers.ReadOnlyField()
    explorer_url          = serializers.ReadOnlyField()
    is_deadline_passed    = serializers.ReadOnlyField()
    creator_display_name  = serializers.SerializerMethodField()

    class Meta:
        model  = Jar
        fields = [
            "id", "chain_jar_id",
            "title", "description", "category", "cover_emoji", "cover_image_url",
            "creator_wallet", "creator_display_name",
            "target_amount_matic", "amount_raised_matic",
            "deadline", "status",
            "is_verified_on_chain", "creation_tx_hash",
            "donor_count",
            # computed
            "progress_percentage", "time_remaining_seconds",
            "can_withdraw", "is_deadline_passed", "explorer_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_creator_display_name(self, obj) -> str:
        try:
            return obj.creator.display_name
        except Exception:
            return obj.creator_wallet[:8] + "…"


# ─────────────────────────────────────────────────────────────────
#  JAR DETAIL (full — includes embedded donation list)
# ─────────────────────────────────────────────────────────────────

class DonationNestedSerializer(serializers.Serializer):
    """
    Minimal donation representation embedded inside JarDetailSerializer.
    Avoids circular import with donations app.
    """
    id              = serializers.IntegerField()
    donor_wallet    = serializers.SerializerMethodField()
    amount_matic    = serializers.DecimalField(max_digits=20, decimal_places=6)
    tx_hash         = serializers.CharField()
    tx_status       = serializers.CharField()
    is_verified     = serializers.BooleanField()
    is_anonymous    = serializers.BooleanField()
    message         = serializers.CharField()
    block_number    = serializers.IntegerField(allow_null=True)
    confirmations   = serializers.IntegerField()
    created_at      = serializers.DateTimeField()
    explorer_url    = serializers.ReadOnlyField()

    def get_donor_wallet(self, obj) -> str:
        return obj.display_wallet  # respects is_anonymous flag


class JarDetailSerializer(JarListSerializer):
    donations         = serializers.SerializerMethodField()
    withdrawal_tx_hash = serializers.CharField()
    withdrawn_at      = serializers.DateTimeField(allow_null=True)

    class Meta(JarListSerializer.Meta):
        fields = JarListSerializer.Meta.fields + [
            "donations",
            "withdrawal_tx_hash", "withdrawn_at",
            "updated_at",
        ]

    def get_donations(self, obj):
        # Most recent 50 confirmed + all pending, newest first
        qs = obj.donations.order_by("-created_at")[:50]
        return DonationNestedSerializer(qs, many=True).data


# ─────────────────────────────────────────────────────────────────
#  JAR CREATE
# ─────────────────────────────────────────────────────────────────

class JarCreateSerializer(serializers.ModelSerializer):
    """
    POST /jars/

    Accepts the jar metadata from the frontend.
    The frontend should call this AFTER the on-chain createJar() tx
    has been submitted (but before confirmation) — passing the tx_hash.
    """
    creation_tx_hash = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Tx hash of the on-chain createJar() call (optional at creation time).",
    )
    chain_jar_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="On-chain jar ID (set after tx confirmation).",
    )

    class Meta:
        model  = Jar
        fields = [
            "title", "description", "category", "cover_emoji", "cover_image_url",
            "target_amount_matic", "deadline",
            "creation_tx_hash", "chain_jar_id",
        ]

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        if len(value) > 120:
            raise serializers.ValidationError("Title max 120 characters (contract limit).")
        return value

    def validate_description(self, value: str) -> str:
        value = value.strip()
        if len(value) > 1000:
            raise serializers.ValidationError("Description max 1000 characters (contract limit).")
        return value

    def validate_target_amount_matic(self, value: Decimal) -> Decimal:
        if value < Decimal("0.01"):
            raise serializers.ValidationError("Minimum target is 0.01 MATIC.")
        if value > Decimal("10000000"):
            raise serializers.ValidationError("Maximum target is 10,000,000 MATIC.")
        return value

    def validate_deadline(self, value) -> object:
        min_deadline = timezone.now() + timezone.timedelta(hours=1)
        max_deadline = timezone.now() + timezone.timedelta(days=365)
        if value < min_deadline:
            raise serializers.ValidationError(
                "Deadline must be at least 1 hour in the future (contract minimum)."
            )
        if value > max_deadline:
            raise serializers.ValidationError(
                "Deadline cannot exceed 1 year from now (contract maximum)."
            )
        return value

    def validate_creation_tx_hash(self, value: str) -> str:
        if not value:
            return value
        import re
        if not re.match(r"^0x[0-9a-fA-F]{64}$", value):
            raise serializers.ValidationError(
                "Invalid transaction hash. Must be 0x + 64 hex characters."
            )
        return value

    def create(self, validated_data: dict) -> Jar:
        request = self.context["request"]
        creator = request.user
        jar = Jar.objects.create(
            creator=creator,
            creator_wallet=creator.wallet_address,
            **validated_data,
        )
        return jar


# ─────────────────────────────────────────────────────────────────
#  JAR UPDATE (metadata only — PATCH by creator)
# ─────────────────────────────────────────────────────────────────

class JarUpdateSerializer(serializers.ModelSerializer):
    """
    PATCH /jars/{id}/

    Only content fields are editable after creation.
    Financial and blockchain fields are immutable.
    """
    class Meta:
        model  = Jar
        fields = [
            "title", "description", "category",
            "cover_emoji", "cover_image_url",
        ]

    def validate(self, attrs: dict) -> dict:
        jar = self.instance
        if jar.status in (JarStatus.WITHDRAWN, JarStatus.EXPIRED):
            raise serializers.ValidationError(
                "Cannot edit a jar that has been withdrawn or expired."
            )
        return attrs


# ─────────────────────────────────────────────────────────────────
#  JAR CONFIRM ON-CHAIN (called after createJar tx confirmed)
# ─────────────────────────────────────────────────────────────────

class JarConfirmSerializer(serializers.Serializer):
    """
    POST /jars/{id}/confirm/
    Called by the frontend once the createJar() tx is confirmed on-chain.
    Sets chain_jar_id and marks is_verified_on_chain = True.
    """
    chain_jar_id     = serializers.IntegerField(min_value=1)
    creation_tx_hash = serializers.CharField(max_length=66)

    def validate_creation_tx_hash(self, value: str) -> str:
        import re
        if not re.match(r"^0x[0-9a-fA-F]{64}$", value):
            raise serializers.ValidationError("Invalid transaction hash.")
        return value


# ─────────────────────────────────────────────────────────────────
#  JAR WITHDRAW (record withdrawal tx)
# ─────────────────────────────────────────────────────────────────

class JarWithdrawSerializer(serializers.Serializer):
    """
    POST /jars/{id}/withdraw/
    Records the withdrawal transaction hash after creator calls withdraw() on-chain.
    """
    withdrawal_tx_hash = serializers.CharField(max_length=66)

    def validate_withdrawal_tx_hash(self, value: str) -> str:
        import re
        if not re.match(r"^0x[0-9a-fA-F]{64}$", value):
            raise serializers.ValidationError("Invalid transaction hash.")
        return value
