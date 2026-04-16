"""
Views for the blockchain app.

Endpoints:
  POST /blockchain/verify/           — manually trigger tx verification
  GET  /blockchain/tx/{tx_hash}/     — get tx verification status
  GET  /blockchain/events/           — contract event log
  GET  /blockchain/events/jar/{id}/  — events for a specific jar
  GET  /blockchain/stats/            — platform-wide aggregate stats
"""
import logging
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum, Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.blockchain.models import TransactionLog, ContractEvent
from apps.blockchain.serializers import (
    TxVerifyRequestSerializer,
    TxStatusSerializer,
    TransactionLogSerializer,
    ContractEventSerializer,
    PlatformStatsSerializer,
)
from apps.donations.models import Donation, TxStatus
from apps.jars.models import Jar, JarStatus
from core.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
#  MANUAL TX VERIFICATION TRIGGER
# ─────────────────────────────────────────────────────────────────

class VerifyThrottle(AnonRateThrottle):
    rate = "20/minute"


class TxVerifyView(APIView):
    """
    POST /blockchain/verify/
    Manually triggers verification for a transaction hash.
    Returns current known status immediately; verification runs async.
    """
    permission_classes = [AllowAny]
    throttle_classes   = [VerifyThrottle]

    @extend_schema(
        tags=["blockchain"],
        summary="Trigger transaction verification",
        request=TxVerifyRequestSerializer,
    )
    def post(self, request):
        serializer = TxVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx_hash = serializer.validated_data["tx_hash"]

        # Queue Celery task
        from apps.blockchain.tasks import verify_single_transaction
        verify_single_transaction.apply_async(args=[tx_hash], countdown=2)

        # Return current DB state immediately
        donation = Donation.objects.filter(tx_hash=tx_hash).first()
        if donation:
            return Response({
                "success": True,
                "message": "Verification task queued.",
                "data": {
                    "tx_hash":      tx_hash,
                    "status":       donation.tx_status,
                    "is_verified":  donation.is_verified,
                    "confirmations": donation.confirmations,
                },
            })

        return Response({
            "success": True,
            "message": "Verification task queued. Transaction not yet in database.",
            "data": {"tx_hash": tx_hash, "status": "unknown"},
        })


# ─────────────────────────────────────────────────────────────────
#  TX STATUS
# ─────────────────────────────────────────────────────────────────

class TxStatusView(APIView):
    """
    GET /blockchain/tx/{tx_hash}/
    Returns the current verification status of a transaction.
    Checks DB first; falls back to live RPC query if not found.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["blockchain"],
        summary="Get transaction verification status",
        responses={200: TxStatusSerializer},
    )
    def get(self, request, tx_hash: str):
        from django.conf import settings

        # ── Check DB first ──
        donation = Donation.objects.filter(tx_hash=tx_hash).first()
        if donation:
            explorer = settings.BLOCKCHAIN.get("EXPLORER_URL", "https://amoy.polygonscan.com")
            data = {
                "tx_hash":        tx_hash,
                "status":         donation.tx_status,
                "is_verified":    donation.is_verified,
                "block_number":   donation.block_number,
                "confirmations":  donation.confirmations,
                "gas_used":       donation.gas_used,
                "gas_price_gwei": donation.gas_price_gwei,
                "verified_at":    donation.verified_at,
                "explorer_url":   f"{explorer}/tx/{tx_hash}",
                "source":         "db",
            }
            return Response({"success": True, "data": data})

        # ── Live RPC fallback ──
        try:
            from apps.blockchain.service import BlockchainService
            svc = BlockchainService()
            receipt = svc.get_receipt(tx_hash)
            explorer = settings.BLOCKCHAIN.get("EXPLORER_URL", "https://amoy.polygonscan.com")

            if receipt:
                data = {
                    "tx_hash":        tx_hash,
                    "status":         "confirmed" if receipt["status"] == 1 else "failed",
                    "is_verified":    receipt["status"] == 1,
                    "block_number":   receipt["blockNumber"],
                    "confirmations":  svc.get_confirmations(receipt["blockNumber"]),
                    "gas_used":       receipt["gasUsed"],
                    "gas_price_gwei": None,
                    "verified_at":    None,
                    "explorer_url":   f"{explorer}/tx/{tx_hash}",
                    "source":         "rpc",
                }
            else:
                data = {
                    "tx_hash":       tx_hash,
                    "status":        "pending",
                    "is_verified":   False,
                    "block_number":  None,
                    "confirmations": 0,
                    "gas_used":      None,
                    "gas_price_gwei": None,
                    "verified_at":   None,
                    "explorer_url":  f"{explorer}/tx/{tx_hash}",
                    "source":        "rpc",
                }

            return Response({"success": True, "data": data})

        except Exception as exc:
            logger.warning("RPC fallback failed for tx %s: %s", tx_hash[:12], exc)
            return Response(
                {"success": False, "error": {"code": "tx_not_found",
                                              "message": "Transaction not found in database or on-chain."}},
                status=status.HTTP_404_NOT_FOUND,
            )


# ─────────────────────────────────────────────────────────────────
#  CONTRACT EVENTS
# ─────────────────────────────────────────────────────────────────

class ContractEventViewSet(ReadOnlyModelViewSet):
    """
    GET /blockchain/events/           — all events (filterable)
    GET /blockchain/events/{id}/      — single event
    """
    serializer_class   = ContractEventSerializer
    pagination_class   = StandardResultsPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = ContractEvent.objects.order_by("-block_number", "log_index")

        event_type = self.request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        chain_jar_id = self.request.query_params.get("chain_jar_id")
        if chain_jar_id:
            qs = qs.filter(chain_jar_id=chain_jar_id)

        wallet = self.request.query_params.get("wallet")
        if wallet:
            qs = qs.filter(emitter_wallet__iexact=wallet)

        return qs

    @extend_schema(tags=["blockchain"], summary="List contract events")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["blockchain"], summary="Get contract event detail")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────
#  PLATFORM STATS (cached — refreshed by Celery)
# ─────────────────────────────────────────────────────────────────

class PlatformStatsView(APIView):
    """
    GET /blockchain/stats/
    Platform-wide aggregate statistics.
    Cached for 60 seconds to avoid hammering the DB on every page load.
    """
    permission_classes = [AllowAny]

    CACHE_KEY = "jarfund_platform_stats"
    CACHE_TTL = 60  # seconds

    @extend_schema(
        tags=["blockchain"],
        summary="Platform aggregate statistics",
        responses={200: PlatformStatsSerializer},
    )
    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached:
            return Response({"success": True, "data": cached, "cached": True})

        now = timezone.now()
        since_24h = now - timezone.timedelta(hours=24)

        # Jar stats
        jar_agg = Jar.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=JarStatus.ACTIVE)),
            completed=Count("id", filter=Q(status=JarStatus.COMPLETED)),
        )

        # Donation stats
        confirmed = Donation.objects.filter(tx_status=TxStatus.CONFIRMED)
        don_agg   = confirmed.aggregate(
            total_raised=Sum("amount_matic"),
            donors=Count("donor_wallet", distinct=True),
            count=Count("id"),
        )

        recent_agg = confirmed.filter(created_at__gte=since_24h).aggregate(
            count=Count("id"),
            raised=Sum("amount_matic"),
        )

        stats = {
            "total_jars":         jar_agg["total"]       or 0,
            "active_jars":        jar_agg["active"]      or 0,
            "completed_jars":     jar_agg["completed"]   or 0,
            "total_raised_matic": don_agg["total_raised"] or Decimal("0"),
            "total_donors":       don_agg["donors"]      or 0,
            "total_donations":    don_agg["count"]       or 0,
            "verified_donations": confirmed.filter(is_verified=True).count(),
            "donations_last_24h": recent_agg["count"]   or 0,
            "raised_last_24h":    recent_agg["raised"]  or Decimal("0"),
        }

        cache.set(self.CACHE_KEY, stats, self.CACHE_TTL)

        return Response({"success": True, "data": stats, "cached": False})
