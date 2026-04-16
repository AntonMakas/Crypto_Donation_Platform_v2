"""
Views for the users app.

Endpoints:
  GET  /auth/nonce/         — get signing challenge for a wallet
  POST /auth/verify/        — verify signature → JWT tokens
  POST /auth/refresh/       — refresh access token
  POST /auth/logout/        — blacklist refresh token
  GET  /auth/profile/       — get own profile
  PATCH /auth/profile/      — update own profile
"""
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import (
    NonceRequestSerializer,
    NonceResponseSerializer,
    WalletVerifySerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
#  NONCE
# ─────────────────────────────────────────────────────────────────

class NonceLimitThrottle(AnonRateThrottle):
    rate = "30/minute"


@method_decorator(never_cache, name="dispatch")
class NonceView(APIView):
    """
    GET /auth/nonce/?wallet=0x…

    Returns the current nonce for a wallet address.
    Creates a new User if this is the wallet's first visit.
    The frontend must have the user sign the returned `message` string.
    """
    permission_classes = [AllowAny]
    throttle_classes   = [NonceLimitThrottle]

    @extend_schema(
        tags=["auth"],
        summary="Get signing nonce for wallet",
        parameters=[
            OpenApiParameter(
                name="wallet",
                description="Ethereum wallet address (0x…)",
                required=True,
                type=str,
            )
        ],
        responses={200: NonceResponseSerializer},
    )
    def get(self, request):
        serializer = NonceRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        wallet = serializer.validated_data["wallet"]

        # get_or_create is atomic — safe against race conditions
        user, created = User.objects.get_or_create(
            wallet_address=wallet,
            defaults={"username": "", "is_verified": False},
        )

        if created:
            logger.info("New wallet registered: %s", wallet)

        message = f"Sign in to JarFund: {user.nonce}"

        return Response({
            "wallet":  wallet,
            "nonce":   user.nonce,
            "message": message,
        })


# ─────────────────────────────────────────────────────────────────
#  VERIFY SIGNATURE → JWT
# ─────────────────────────────────────────────────────────────────

class VerifyLimitThrottle(AnonRateThrottle):
    rate = "10/minute"


class WalletVerifyView(APIView):
    """
    POST /auth/verify/

    Body: { "wallet": "0x…", "signature": "0x…" }
    Response: { "access": "…", "refresh": "…", "user": { … } }

    Verifies the MetaMask signature against the stored nonce.
    On success: marks user as verified, rotates nonce, returns JWTs.
    """
    permission_classes = [AllowAny]
    throttle_classes   = [VerifyLimitThrottle]

    @extend_schema(
        tags=["auth"],
        summary="Verify wallet signature and get JWT tokens",
        request=WalletVerifySerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access":  {"type": "string"},
                    "refresh": {"type": "string"},
                    "user":    {"type": "object"},
                },
            }
        },
    )
    def post(self, request):
        serializer = WalletVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user   = serializer.validated_data["user"]
        tokens = serializer.get_tokens()

        logger.info("Wallet authenticated: %s", user.wallet_address)

        return Response({
            "success": True,
            "data": {
                **tokens,
                "user": UserProfileSerializer(
                    user, context={"request": request}
                ).data,
            },
        })


# ─────────────────────────────────────────────────────────────────
#  TOKEN REFRESH
# ─────────────────────────────────────────────────────────────────

class TokenRefreshView(APIView):
    """
    POST /auth/refresh/
    Body: { "refresh": "…" }
    Response: { "access": "…" }
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=["auth"], summary="Refresh access token")
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"success": False, "error": {"code": "missing_token", "message": "Refresh token required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                "success": True,
                "data": {"access": str(refresh.access_token)},
            })
        except TokenError as e:
            return Response(
                {"success": False, "error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# ─────────────────────────────────────────────────────────────────
#  LOGOUT (blacklist refresh token)
# ─────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /auth/logout/
    Body: { "refresh": "…" }
    Blacklists the refresh token so it can't be used again.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="Logout — blacklist refresh token")
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"success": False, "error": {"code": "missing_token", "message": "Refresh token required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Token blacklisted for user %s", request.user.wallet_address)
            return Response({"success": True, "message": "Logged out successfully."})
        except TokenError as e:
            return Response(
                {"success": False, "error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ─────────────────────────────────────────────────────────────────
#  PROFILE
# ─────────────────────────────────────────────────────────────────

class ProfileView(APIView):
    """
    GET  /auth/profile/ — returns own full profile
    PATCH /auth/profile/ — updates username, bio, avatar_url
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="Get own profile", responses={200: UserProfileSerializer})
    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        tags=["auth"],
        summary="Update own profile",
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "success": True,
            "data": UserProfileSerializer(request.user, context={"request": request}).data,
        })
