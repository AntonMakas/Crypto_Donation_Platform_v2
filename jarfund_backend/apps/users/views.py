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

class NonceLimitThrottle(AnonRateThrottle):
    rate = "30/minute"


@method_decorator(never_cache, name="dispatch")
class NonceView(APIView):
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

class VerifyLimitThrottle(AnonRateThrottle):
    rate = "10/minute"


class WalletVerifyView(APIView):
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
            try:
                token.blacklist()
            except AttributeError:
                # token_blacklist app is not installed; skip blacklisting
                pass
            logger.info("Token invalidated for user %s", request.user.wallet_address)
            return Response({"success": True, "message": "Logged out successfully."})
        except TokenError as e:
            return Response(
                {"success": False, "error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

class ProfileView(APIView):
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
