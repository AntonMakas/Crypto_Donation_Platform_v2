"""
JarFund — Root URL Configuration
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# ── Dynamically set admin URL from settings (obscured in production) ──
ADMIN_URL = getattr(settings, "ADMIN_URL", "admin/")

urlpatterns = [
    # ── Django Admin ──
    path(ADMIN_URL, admin.site.urls),

    # ── API v1 ──
    path("api/v1/", include([
        # Auth (wallet-based)
        path("auth/",      include("apps.users.urls",     namespace="users")),

        # Jars
        path("jars/",      include("apps.jars.urls",      namespace="jars")),

        # Donations
        path("donations/", include("apps.donations.urls", namespace="donations")),

        # Blockchain verification
        path("blockchain/",include("apps.blockchain.urls",namespace="blockchain")),
    ])),

    # ── OpenAPI Schema & Docs ──
    path("api/schema/",  SpectacularAPIView.as_view(),   name="schema"),
    path("api/docs/",    SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/",   SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),

    # ── Health check ──
    path("health/",      include("core.urls")),
]

# ── Serve media files in development ──
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ── Admin site branding ──
admin.site.site_header  = "JarFund Admin"
admin.site.site_title   = "JarFund"
admin.site.index_title  = "Platform Administration"
