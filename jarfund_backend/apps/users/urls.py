from django.urls import path
from .views import (
    NonceView,
    WalletVerifyView,
    TokenRefreshView,
    LogoutView,
    ProfileView,
)

app_name = "users"

urlpatterns = [
    # ── Wallet auth ──
    path("nonce/",   NonceView.as_view(),        name="nonce"),
    path("verify/",  WalletVerifyView.as_view(),  name="verify"),
    path("refresh/", TokenRefreshView.as_view(),  name="refresh"),
    path("logout/",  LogoutView.as_view(),         name="logout"),

    # ── Profile ──
    path("profile/", ProfileView.as_view(),        name="profile"),
]
