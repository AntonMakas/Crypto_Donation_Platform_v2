"""
URL configuration for the jars app.

  GET    /api/v1/jars/               — list / explore
  POST   /api/v1/jars/               — create jar
  GET    /api/v1/jars/my/            — my jars (auth)
  GET    /api/v1/jars/{id}/          — jar detail
  PATCH  /api/v1/jars/{id}/          — update metadata (creator)
  POST   /api/v1/jars/{id}/confirm/  — confirm on-chain
  POST   /api/v1/jars/{id}/withdraw/ — record withdrawal
  GET    /api/v1/jars/{id}/donations/— paginated donations
  GET    /api/v1/jars/{id}/stats/    — donation stats
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JarViewSet, MyJarsView

app_name = "jars"

router = DefaultRouter()
router.register(r"", JarViewSet, basename="jar")

urlpatterns = [
    # Must come BEFORE router to avoid being swallowed by {pk} pattern
    path("my/", MyJarsView.as_view(), name="my-jars"),

    # Router handles: list, create, retrieve, partial_update,
    # and the @action decorators: confirm, withdraw, donations, stats
    path("", include(router.urls)),
]
