"""
django-filter FilterSets for advanced API querying.

Usage:
  GET /api/v1/jars/?status=active&category=education&min_target=10&ordering=-amount_raised_matic
"""
import django_filters
from django.db import models

from apps.jars.models import Jar, JarStatus, JarCategory


class JarFilter(django_filters.FilterSet):
    """
    Advanced filter for the jar list endpoint.

    Supported query params:
      status             — exact: active | completed | expired | withdrawn
      category           — exact: education | technology | …
      min_target         — amount_raised_matic >= value
      max_target         — amount_raised_matic <= value
      creator_wallet     — case-insensitive exact match
      is_verified        — true | false
      deadline_before    — deadline <= date
      deadline_after     — deadline >= date
      has_raised         — amount_raised_matic > 0
    """
    status   = django_filters.ChoiceFilter(choices=JarStatus.choices)
    category = django_filters.ChoiceFilter(choices=JarCategory.choices)

    min_target = django_filters.NumberFilter(
        field_name="target_amount_matic", lookup_expr="gte"
    )
    max_target = django_filters.NumberFilter(
        field_name="target_amount_matic", lookup_expr="lte"
    )

    min_raised = django_filters.NumberFilter(
        field_name="amount_raised_matic", lookup_expr="gte"
    )

    creator_wallet = django_filters.CharFilter(
        field_name="creator_wallet", lookup_expr="iexact"
    )

    is_verified = django_filters.BooleanFilter(
        field_name="is_verified_on_chain"
    )

    deadline_before = django_filters.DateTimeFilter(
        field_name="deadline", lookup_expr="lte"
    )
    deadline_after = django_filters.DateTimeFilter(
        field_name="deadline", lookup_expr="gte"
    )

    has_raised = django_filters.BooleanFilter(method="filter_has_raised")

    def filter_has_raised(self, queryset, name, value):
        if value:
            return queryset.filter(amount_raised_matic__gt=0)
        return queryset.filter(amount_raised_matic=0)

    class Meta:
        model  = Jar
        fields = [
            "status", "category",
            "min_target", "max_target", "min_raised",
            "creator_wallet", "is_verified",
            "deadline_before", "deadline_after",
            "has_raised",
        ]
