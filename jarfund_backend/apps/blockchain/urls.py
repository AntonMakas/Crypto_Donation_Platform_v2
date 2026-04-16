"""
URL configuration for the blockchain app.

  POST /api/v1/blockchain/verify/              — trigger tx verification
  GET  /api/v1/blockchain/tx/{tx_hash}/        — tx status
  GET  /api/v1/blockchain/events/              — contract event log
  GET  /api/v1/blockchain/events/{id}/         — single event
  GET  /api/v1/blockchain/stats/               — platform stats
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TxVerifyView,
    TxStatusView,
    ContractEventViewSet,
    PlatformStatsView,
)

app_name = "blockchain"

router = DefaultRouter()
router.register(r"events", ContractEventViewSet, basename="event")

urlpatterns = [
    path("verify/",          TxVerifyView.as_view(),                       name="verify"),
    path("tx/<str:tx_hash>/", TxStatusView.as_view(),                      name="tx-status"),
    path("stats/",           PlatformStatsView.as_view(),                  name="stats"),
    path("",                 include(router.urls)),
]
