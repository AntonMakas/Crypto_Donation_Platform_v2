"""
URL configuration for the donations app.

  POST /api/v1/donations/             — submit donation tx
  GET  /api/v1/donations/             — list donations (filterable)
  GET  /api/v1/donations/my/          — my donations (auth)
  GET  /api/v1/donations/leaderboard/ — top donors
  GET  /api/v1/donations/{id}/        — single donation detail
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DonationCreateView, DonationViewSet, MyDonationsView, DonorLeaderboardView

app_name = "donations"

router = DefaultRouter()
router.register(r"", DonationViewSet, basename="donation")

urlpatterns = [
    # Custom paths must come BEFORE the router catch-all
    path("my/",          MyDonationsView.as_view(),      name="my-donations"),
    path("leaderboard/", DonorLeaderboardView.as_view(), name="leaderboard"),

    # POST to root — create donation (separate view to enforce strict auth)
    path("",             DonationCreateView.as_view(),   name="create"),

    # Router for GET list + GET detail
    path("",             include(router.urls)),
]
