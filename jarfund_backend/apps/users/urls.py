"""
URL configuration for the users / auth app.

  GET  /api/v1/auth/nonce/    — get signing challenge
  POST /api/v1/auth/verify/   — verify signature → JWT
  POST /api/v1/auth/refresh/  — refresh access token
  POST /api/v1/auth/logout/   — blacklist refresh token
  GET  /api/v1/auth/profile/  — get own profile
  PATCH /api/v1/auth/profile/ — update own profile
"""
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
