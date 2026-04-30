"""
Views for the jars app.

Endpoints:
  GET    /jars/                 — paginated list with filters
  POST   /jars/                 — create a new jar (auth required)
  GET    /jars/{id}/            — jar detail with donations
  PATCH  /jars/{id}/            — update metadata (creator only)
  DELETE /jars/{id}/            — soft-delete (creator + active only)
  POST   /jars/{id}/confirm/    — confirm creation tx on-chain
  POST   /jars/{id}/withdraw/   — record withdrawal tx
  GET    /jars/{id}/donations/  — paginated donation list for a jar
  GET    /jars/{id}/stats/      — donation statistics for a jar
  GET    /jars/my/              — jars created by the current user
"""
import logging
from decimal import Decimal

from django.db.models import Sum, Count, Max, Avg, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
)

from apps.jars.models import Jar, JarStatus
from apps.jars.serializers import (
    JarListSerializer,
    JarDetailSerializer,
    JarCreateSerializer,
    JarUpdateSerializer,
    JarConfirmSerializer,
    JarWithdrawSerializer,
)
from apps.donations.models import Donation, TxStatus
from apps.donations.serializers import DonationListSerializer, DonationStatsSerializer
from core.pagination import StandardResultsPagination
from core.permissions import IsJarCreator, IsOwnerOrReadOnly

logger = logging.getLogger(__name__)


class CreateJarThrottle(UserRateThrottle):
    rate = "10/minute"


# ─────────────────────────────────────────────────────────────────
#  JAR VIEWSET
# ─────────────────────────────────────────────────────────────────

class JarViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    GenericViewSet,
):
    """
    Core jar CRUD. List, detail, and create are here.
    Patch, confirm, and withdraw are separate @action methods.
    """
    pagination_class    = StandardResultsPagination
    filter_backends     = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Search: ?search=community
    search_fields       = ["title", "description", "creator_wallet"]

    # Filter: ?status=active&category=education
    filterset_fields    = ["status", "category", "is_verified_on_chain"]

    # Order: ?ordering=-amount_raised_matic
    ordering_fields     = ["created_at", "deadline", "amount_raised_matic", "donor_count"]
    ordering            = ["-created_at"]

    def get_queryset(self):
        qs = Jar.objects.select_related("creator").prefetch_related(
            # Prefetch only the 20 most recent confirmed donations for list
            # (detail fetches all via DonationListView)
        )

        # Filter by creator wallet if provided
        wallet = self.request.query_params.get("creator_wallet")
        if wallet:
            qs = qs.filter(creator_wallet__iexact=wallet)

        # Filter active-only by default on the explore page
        # (pass ?include_all=1 to see all statuses)
        if self.action == "list":
            include_all = self.request.query_params.get("include_all", "0")
            if include_all != "1" and "status" not in self.request.query_params:
                qs = qs.filter(status__in=[JarStatus.ACTIVE, JarStatus.COMPLETED])

        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return JarDetailSerializer
        if self.action == "create":
            return JarCreateSerializer
        if self.action in ("update", "partial_update"):
            return JarUpdateSerializer
        if self.action == "confirm":
            return JarConfirmSerializer
        if self.action == "withdraw":
            return JarWithdrawSerializer
        return JarListSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "donations", "stats"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action == "create":
            return [CreateJarThrottle()]
        return super().get_throttles()

    # ── CREATE ────────────────────────────────────────────────────
    @extend_schema(tags=["jars"], summary="Create a new fundraising jar")
    def create(self, request, *args, **kwargs):
        serializer = JarCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        jar = serializer.save()
        logger.info(
            "Jar #%s created by %s: '%s'",
            jar.id, request.user.wallet_address, jar.title,
        )
        return Response(
            {"success": True, "data": JarDetailSerializer(jar, context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )

    # ── LIST ──────────────────────────────────────────────────────
    @extend_schema(tags=["jars"], summary="List / explore fundraising jars")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # ── RETRIEVE ──────────────────────────────────────────────────
    @extend_schema(tags=["jars"], summary="Get jar detail with donations")
    def retrieve(self, request, *args, **kwargs):
        jar = self.get_object()
        return Response({
            "success": True,
            "data": JarDetailSerializer(jar, context={"request": request}).data,
        })

    # ── PARTIAL UPDATE (PATCH) ────────────────────────────────────
    @extend_schema(tags=["jars"], summary="Update jar metadata (creator only)")
    def partial_update(self, request, *args, **kwargs):
        jar = self.get_object()
        self.check_object_permissions(request, jar)

        if jar.creator != request.user:
            return Response(
                {"success": False, "error": {"code": "forbidden", "message": "Only the jar creator can edit this jar."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = JarUpdateSerializer(jar, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "success": True,
            "data": JarDetailSerializer(jar, context={"request": request}).data,
        })

    # ── CONFIRM ON-CHAIN ──────────────────────────────────────────
    @extend_schema(tags=["jars"], summary="Confirm jar creation on-chain")
    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        """
        Called by frontend after createJar() tx is confirmed.
        Sets chain_jar_id and marks is_verified_on_chain = True.
        Triggers on-chain verification via Celery.
        """
        jar = self.get_object()

        if jar.creator != request.user:
            return Response(
                {"success": False, "error": {"code": "forbidden", "message": "Not your jar."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = JarConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chain_jar_id     = serializer.validated_data["chain_jar_id"]
        creation_tx_hash = serializer.validated_data["creation_tx_hash"]

        # Prevent overwrite if already confirmed
        if jar.is_verified_on_chain:
            return Response(
                {"success": False, "error": {"code": "already_confirmed", "message": "Jar already confirmed on-chain."}},
                status=status.HTTP_409_CONFLICT,
            )

        # Check chain_jar_id is not already taken
        if Jar.objects.filter(chain_jar_id=chain_jar_id).exclude(pk=jar.pk).exists():
            return Response(
                {"success": False, "error": {"code": "duplicate_chain_id", "message": "chain_jar_id already in use."}},
                status=status.HTTP_409_CONFLICT,
            )

        jar.chain_jar_id     = chain_jar_id
        jar.creation_tx_hash = creation_tx_hash
        jar.save(update_fields=["chain_jar_id", "creation_tx_hash", "updated_at"])

        # Queue on-chain verification
        from apps.blockchain.tasks import verify_jar_creation
        verify_jar_creation.apply_async(args=[jar.id], countdown=10)

        logger.info(
            "Jar #%s confirm submitted: chain_id=%s tx=%s",
            jar.id, chain_jar_id, creation_tx_hash[:12],
        )

        return Response({
            "success": True,
            "data": JarDetailSerializer(jar, context={"request": request}).data,
        })

    # ── WITHDRAW ──────────────────────────────────────────────────
    @extend_schema(tags=["jars"], summary="Record jar withdrawal transaction")
    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        """
        Called by frontend after creator calls withdraw() on-chain.
        Records the withdrawal tx hash and marks the jar as Withdrawn.
        """
        jar = self.get_object()

        if jar.creator != request.user:
            return Response(
                {"success": False, "error": {"code": "forbidden", "message": "Not your jar."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if jar.status == JarStatus.WITHDRAWN:
            return Response(
                {"success": False, "error": {"code": "already_withdrawn", "message": "Already withdrawn."}},
                status=status.HTTP_409_CONFLICT,
            )

        if not jar.can_withdraw:
            return Response(
                {"success": False, "error": {
                    "code": "withdrawal_conditions_not_met",
                    "message": "Withdrawal conditions not met: deadline not reached and target not achieved.",
                }},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = JarWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        jar.withdrawal_tx_hash = serializer.validated_data["withdrawal_tx_hash"]
        jar.status             = JarStatus.WITHDRAWN
        jar.withdrawn_at       = timezone.now()
        jar.save(update_fields=["withdrawal_tx_hash", "status", "withdrawn_at", "updated_at"])

        logger.info(
            "Jar #%s marked WITHDRAWN by %s. Tx: %s",
            jar.id, request.user.wallet_address, jar.withdrawal_tx_hash[:12],
        )

        return Response({
            "success": True,
            "data": JarDetailSerializer(jar, context={"request": request}).data,
        })

    # ── DONATIONS LIST ────────────────────────────────────────────
    @extend_schema(tags=["jars"], summary="List donations for a jar")
    @action(detail=True, methods=["get"], url_path="donations")
    def donations(self, request, pk=None):
        jar = self.get_object()

        qs = Donation.objects.filter(jar=jar).order_by("-created_at")

        # filter by status
        tx_status = request.query_params.get("tx_status")
        if tx_status:
            qs = qs.filter(tx_status=tx_status)



        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = DonationListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        return Response({
            "success": True,
            "data": DonationListSerializer(qs, many=True, context={"request": request}).data,
        })

    # ── DONATION STATS ────────────────────────────────────────────
    @extend_schema(tags=["jars"], summary="Donation statistics for a jar")
    @action(detail=True, methods=["get"], url_path="stats")
    def stats(self, request, pk=None):
        jar = self.get_object()

        confirmed = Donation.objects.filter(jar=jar, tx_status=TxStatus.CONFIRMED)
        pending   = Donation.objects.filter(jar=jar, tx_status=TxStatus.PENDING)

        agg = confirmed.aggregate(
            total=Sum("amount_matic"),
            count=Count("id"),
            donors=Count("donor_wallet", distinct=True),
            largest=Max("amount_matic"),
            average=Avg("amount_matic"),
            latest=Max("created_at"),
        )

        stats_data = {
            "total_confirmed":   agg["total"]   or Decimal("0"),
            "total_pending":     pending.aggregate(t=Sum("amount_matic"))["t"] or Decimal("0"),
            "donor_count":       agg["donors"]  or 0,
            "donation_count":    agg["count"]   or 0,
            "largest_donation":  agg["largest"] or Decimal("0"),
            "average_donation":  agg["average"] or Decimal("0"),
            "latest_donation_at": agg["latest"],
        }

        serializer = DonationStatsSerializer(stats_data)
        return Response({"success": True, "data": serializer.data})


# ─────────────────────────────────────────────────────────────────
#  MY JARS (authenticated user's own jars)
# ─────────────────────────────────────────────────────────────────

class MyJarsView(APIView):
    """
    GET /jars/my/
    Returns all jars created by the currently authenticated user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["jars"], summary="Get jars created by the current user")
    def get(self, request):
        jars = Jar.objects.filter(
            creator=request.user
        ).order_by("-created_at")

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(jars, request)
        serializer = JarListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)
