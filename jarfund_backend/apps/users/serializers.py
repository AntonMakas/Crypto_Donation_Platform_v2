"""
Serializers for the users app.

Authentication flow:
  1. GET  /auth/nonce/?wallet=0x…        → returns { nonce }
  2. POST /auth/verify/                  → { wallet, signature } → { access, refresh, user }
  3. POST /auth/refresh/                 → { refresh } → { access }
  4. POST /auth/logout/                  → blacklists refresh token
"""
import re
from eth_account import Account
from eth_account.messages import encode_defunct

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

_ETH_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _checksum(address: str) -> str:
    """Return EIP-55 checksum address."""
    from web3 import Web3
    return Web3.to_checksum_address(address)


# ─────────────────────────────────────────────────────────────────
#  NONCE REQUEST
# ─────────────────────────────────────────────────────────────────

class NonceRequestSerializer(serializers.Serializer):
    """
    GET /auth/nonce/?wallet=0x…
    Returns the current nonce for a wallet. Creates the user if first visit.
    """
    wallet = serializers.CharField(max_length=42)

    def validate_wallet(self, value: str) -> str:
        if not _ETH_RE.match(value):
            raise serializers.ValidationError(
                "Invalid Ethereum address. Must be 0x followed by 40 hex characters."
            )
        return _checksum(value)


class NonceResponseSerializer(serializers.Serializer):
    """Response schema for the nonce endpoint (used by drf-spectacular)."""
    wallet  = serializers.CharField()
    nonce   = serializers.CharField()
    message = serializers.CharField(help_text="The full string the user must sign.")


# ─────────────────────────────────────────────────────────────────
#  SIGNATURE VERIFICATION
# ─────────────────────────────────────────────────────────────────

class WalletVerifySerializer(serializers.Serializer):
    """
    POST /auth/verify/
    Verifies a MetaMask signature and returns JWT tokens.

    The frontend must sign exactly:
        "Sign in to JarFund: {nonce}"
    """
    wallet    = serializers.CharField(max_length=42)
    signature = serializers.CharField(max_length=132)

    def validate_wallet(self, value: str) -> str:
        if not _ETH_RE.match(value):
            raise serializers.ValidationError("Invalid Ethereum address.")
        return _checksum(value)

    def validate_signature(self, value: str) -> str:
        if not value.startswith("0x") or len(value) != 132:
            raise serializers.ValidationError(
                "Invalid signature format. Must be 0x-prefixed 65-byte hex string (132 chars)."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        wallet    = attrs["wallet"]
        signature = attrs["signature"]

        # Fetch or create user
        user, created = User.objects.get_or_create(
            wallet_address=wallet,
            defaults={"username": "", "is_verified": False},
        )

        # Build the exact message the frontend signed
        message = f"Sign in to JarFund: {user.nonce}"

        # Recover the signer from the signature
        try:
            msg_hash = encode_defunct(text=message)
            recovered = Account.recover_message(msg_hash, signature=signature)
            recovered = _checksum(recovered)
        except Exception as exc:
            raise serializers.ValidationError(
                {"signature": f"Could not recover signer from signature: {exc}"}
            )

        # Verify recovered address matches claimed wallet
        if recovered.lower() != wallet.lower():
            raise serializers.ValidationError(
                {"signature": "Signature does not match the provided wallet address."}
            )

        # All good — mark user as verified and rotate nonce
        user.is_verified  = True
        user.last_login_at = timezone.now()
        user.save(update_fields=["is_verified", "last_login_at", "updated_at"])
        user.rotate_nonce()

        attrs["user"] = user
        return attrs

    def get_tokens(self) -> dict:
        """Generate JWT access + refresh tokens for the verified user."""
        user    = self.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return {
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
        }


# ─────────────────────────────────────────────────────────────────
#  USER PROFILE
# ─────────────────────────────────────────────────────────────────

class UserPublicSerializer(serializers.ModelSerializer):
    """
    Minimal public profile — safe to expose in donation lists, jar cards, etc.
    Never exposes nonce, email, or internal fields.
    """
    display_name  = serializers.ReadOnlyField()
    short_wallet  = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            "id", "wallet_address", "short_wallet",
            "display_name", "username", "avatar_url",
            "is_verified", "created_at",
        ]
        read_only_fields = fields

    def get_short_wallet(self, obj) -> str:
        return obj.get_short_wallet()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full profile — returned to the authenticated user only.
    Includes stats and editable fields.
    """
    display_name   = serializers.ReadOnlyField()
    short_wallet   = serializers.SerializerMethodField()
    total_donated  = serializers.ReadOnlyField()
    total_raised   = serializers.ReadOnlyField()
    jars_count     = serializers.SerializerMethodField()
    donations_count = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            "id", "wallet_address", "short_wallet", "display_name",
            "username", "bio", "avatar_url",
            "is_verified", "is_staff",
            "total_donated", "total_raised",
            "jars_count", "donations_count",
            "created_at", "last_login_at",
        ]
        read_only_fields = [
            "id", "wallet_address", "short_wallet", "display_name",
            "is_verified", "is_staff",
            "total_donated", "total_raised",
            "jars_count", "donations_count",
            "created_at", "last_login_at",
        ]

    def get_short_wallet(self, obj) -> str:
        return obj.get_short_wallet()

    def get_jars_count(self, obj) -> int:
        return obj.jars.count()

    def get_donations_count(self, obj) -> int:
        return obj.donations_made.count()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """PATCH /profile/ — only username, bio, avatar_url are editable."""
    class Meta:
        model  = User
        fields = ["username", "bio", "avatar_url"]

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if len(value) > 80:
            raise serializers.ValidationError("Username max 80 characters.")
        return value
