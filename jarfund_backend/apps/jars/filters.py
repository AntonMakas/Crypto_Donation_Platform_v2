import django_filters

from apps.jars.models import Jar, JarCategory, JarStatus


class JarFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=JarStatus.choices, method="filter_status")
    category = django_filters.ChoiceFilter(choices=JarCategory.choices)
    min_target = django_filters.NumberFilter(field_name="target_amount_matic", lookup_expr="gte")
    max_target = django_filters.NumberFilter(field_name="target_amount_matic", lookup_expr="lte")
    min_raised = django_filters.NumberFilter(field_name="amount_raised_matic", lookup_expr="gte")
    creator_wallet = django_filters.CharFilter(field_name="creator_wallet", lookup_expr="iexact")
    is_verified = django_filters.BooleanFilter(field_name="is_verified_on_chain")
    deadline_before = django_filters.DateTimeFilter(field_name="deadline", lookup_expr="lte")
    deadline_after = django_filters.DateTimeFilter(field_name="deadline", lookup_expr="gte")
    has_raised = django_filters.BooleanFilter(method="filter_has_raised")

    def filter_status(self, queryset, name, value):
        if value == JarStatus.COMPLETED:
            return queryset.filter(status__in=[JarStatus.COMPLETED, JarStatus.WITHDRAWN])
        return queryset.filter(status=value)

    def filter_has_raised(self, queryset, name, value):
        if value:
            return queryset.filter(amount_raised_matic__gt=0)
        return queryset.filter(amount_raised_matic=0)

    class Meta:
        model = Jar
        fields = [
            "status",
            "category",
            "min_target",
            "max_target",
            "min_raised",
            "creator_wallet",
            "is_verified",
            "deadline_before",
            "deadline_after",
            "has_raised",
        ]
