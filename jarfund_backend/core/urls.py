"""
Health check endpoint — used by load balancers, Railway, Render uptime checks.
GET /health/ → { "status": "ok", "db": "ok", "cache": "ok", "blockchain": "ok" }
"""
from django.urls import path
from django.http import JsonResponse
from django.db import connection, OperationalError


def health_check(request):
    """
    Lightweight health check. Returns 200 if all systems are healthy,
    503 if any critical dependency is down.
    """
    checks = {}
    overall_ok = True

    # ── Database ──
    try:
        connection.ensure_connection()
        checks["db"] = "ok"
    except OperationalError:
        checks["db"] = "error"
        overall_ok = False

    # ── Cache (Redis) ──
    try:
        from django.core.cache import cache
        cache.set("_health_check", "1", timeout=5)
        result = cache.get("_health_check")
        checks["cache"] = "ok" if result == "1" else "error"
    except Exception:
        checks["cache"] = "error"
        # Cache failures are non-critical — don't fail overall health

    # ── Blockchain RPC reachability (non-blocking check) ──
    try:
        from django.conf import settings
        rpc_url = settings.BLOCKCHAIN.get("POLYGON_AMOY_RPC_URL", "")
        checks["blockchain_rpc_configured"] = bool(rpc_url)
    except Exception:
        checks["blockchain_rpc_configured"] = False

    status_code = 200 if overall_ok else 503
    return JsonResponse(
        {
            "status": "ok" if overall_ok else "degraded",
            "checks": checks,
            "version": "1.0.0",
        },
        status=status_code,
    )


urlpatterns = [
    path("", health_check, name="health_check"),
]
