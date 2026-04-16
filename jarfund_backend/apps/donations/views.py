"""
Views for the donations app.

Endpoints:
  POST /donations/          — submit a new donation tx (auth required)
  GET  /donations/          — list all donations (admin / debug)
  GET  /donations/{id}/     — single donation detail
  GET  /donations/my/       — donations made by current user
  GET  /donations/leaderboard/ — top donors by total amount
"""
import logging
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.donations.models import Donation, TxStatus
from apps.donations.serializers import (
    DonationCreateSerializer,
    DonationListSerializer,
    DonationDetailSerializer,
)
from core.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class DonateLimitThrottle(UserRateThrottle):
    scope = "donate"
    rate  = "30/minute"


# ─────────────────────────────────────────────────────────────────
#  DONATION CREATE
# ─────────────────────────────────────────────────────────────────

class DonationCreateView(APIView):
    """
    POST /donations/

    Records a newly submitted donation transaction.
    Immediately queues a Celery verification task.

    Request body:
        {
            "jar_id":       1,
            "donor_wallet": "0x…",
            "amount_matic": "0.5",
            "amount_wei":   "500000000000000000",
            "tx_hash":      "0x…",
            "message":      "Good luck!",   (optional)
            "is_anonymous": false           (optional)
        }
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [DonateLimitThrottle]

    @extend_schema(
        tags=["donations"],
        summary="Submit a donation transaction",
        request=DonationCreateSerializer,
        responses={201: DonationDetailSerializer},
    )
    def post(self, request):
        # Enforce that donor_wallet matches authenticated user's wallet
        # (prevents submitting someone else's tx)
        submitted_wallet = request.data.get("donor_wallet", "")
        if submitted_wallet.lower() != request.user.wallet_address.lower():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code":    "wallet_mismatch",
                        "message": "donor_wallet must match your authenticated wallet address.",
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DonationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        donation = serializer.save()

        logger.info(
            "Donation #%s recorded: %s MATIC from %s to Jar #%s — tx: %s",
            donation.id,
            donation.amount_matic,
            donation.donor_wallet[:10],
            donation.jar_id,
            donation.tx_hash[:12],
        )

        return Response(
            {
                "success": True,
                "message": "Donation recorded. Verification in progress.",
                "data":    DonationDetailSerializer(donation, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────────────────────────
#  DONATION READ — ViewSet
# ─────────────────────────────────────────────────────────────────

class DonationViewSet(ReadOnlyModelViewSet):
    """
    GET /donations/      — all donations (filterable)
    GET /donations/{id}/ — single donation
    """
    pagination_class   = StandardResultsPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Donation.objects.select_related("jar").order_by("-created_at")

        # Filter by ?jar_id=
        jar_id = self.request.query_params.get("jar_id")
        if jar_id:
            qs = qs.filter(jar_id=jar_id)

        # Filter by ?donor_wallet=
        wallet = self.request.query_params.get("donor_wallet")
        if wallet:
            qs = qs.filter(donor_wallet__iexact=wallet)

        # Filter by ?tx_status=confirmed
        tx_status = self.request.query_params.get("tx_status")
        if tx_status:
            qs = qs.filter(tx_status=tx_status)

        # Filter by ?is_verified=true
        is_verified = self.request.query_params.get("is_verified")
        if is_verified is not None:
            qs = qs.filter(is_verified=(is_verified.lower() == "true"))

        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DonationDetailSerializer
        return DonationListSerializer

    @extend_schema(tags=["donations"], summary="List all donations")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["donations"], summary="Get donation detail")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────
#  MY DONATIONS
# ─────────────────────────────────────────────────────────────────

class MyDonationsView(APIView):
    """
    GET /donations/my/
    Returns all donations made by the current user's wallet.
    Includes summary stats.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["donations"], summary="Get current user's donations")
    def get(self, request):
        wallet = request.user.wallet_address

        qs = Donation.objects.filter(
            donor_wallet__iexact=wallet,
        ).select_related("jar").order_by("-created_at")

        # Stats
        confirmed_qs = qs.filter(tx_status=TxStatus.CONFIRMED)
        agg = confirmed_qs.aggregate(
            total=Sum("amount_matic"),
            count=Count("id"),
        )

        # Paginate
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = DonationListSerializer(page, many=True, context={"request": request})

        response = paginator.get_paginated_response(serializer.data)
        # Inject stats into response
        response.data["stats"] = {
            "total_donated_matic": str(agg["total"] or Decimal("0")),
            "confirmed_count":     agg["count"] or 0,
            "pending_count":       qs.filter(tx_status=TxStatus.PENDING).count(),
        }
        return response


# ─────────────────────────────────────────────────────────────────
#  LEADERBOARD (top donors)
# ─────────────────────────────────────────────────────────────────

class DonorLeaderboardView(APIView):
    """
    GET /donations/leaderboard/?limit=10
    Returns top donors by total confirmed MATIC donated.
    Anonymous donations are excluded from leaderboard.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=["donations"], summary="Top donors leaderboard")
    def get(self, request):
        limit = min(int(request.query_params.get("limit", 10)), 50)

        leaderboard = (
            Donation.objects
            .filter(
                tx_status=TxStatus.CONFIRMED,
                is_anonymous=False,
            )
            .values("donor_wallet")
            .annotate(
                total_donated=Sum("amount_matic"),
                donation_count=Count("id"),
            )
            .order_by("-total_donated")[:limit]
        )

        return Response({
            "success": True,
            "data": list(leaderboard),
        })
