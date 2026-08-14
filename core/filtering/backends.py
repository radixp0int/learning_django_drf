from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from core.ordering import set_applied_ordering


class CustomFilterBackend(DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return super().filter_queryset(request, queryset, view)


class CustomOrderingFilter(OrderingFilter):
    ordering_param = 'sort'

    def get_ordering(self, request, queryset, view):
        """
        Translates 'field,asc' -> 'field' and 'field,desc' -> '-field'

        Publishes the resolved ordering via core.ordering so the paginator can
        report what was actually applied instead of echoing the raw parameter.
        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            ordering = []

            for i in range(0, len(fields), 2):
                field = fields[i]
                if i + 1 < len(fields):
                    direction = fields[i + 1].lower()
                    if direction == 'desc':
                        field = f'-{field}'
                valid = self.remove_invalid_fields(queryset, [field.lstrip('-')], view, request)
                if valid:
                    ordering.append(field)

            if ordering:
                set_applied_ordering(request, ordering, is_default=False)
                return ordering

        # No sort param, or every requested field was rejected as invalid.
        default_ordering = self.get_default_ordering(view)
        set_applied_ordering(request, default_ordering, is_default=True)
        return default_ordering
