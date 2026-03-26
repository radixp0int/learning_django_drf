from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

class CustomFilterBackend(DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return super().filter_queryset(request, queryset, view)

class CustomOrderingFilter(OrderingFilter):
    # Change the query parameter name from 'ordering' to 'sort'
    ordering_param = 'sort'

    def get_ordering(self, request, queryset, view):
        """
        Translates 'field,asc' -> 'field' and 'field,desc' -> '-field'
        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            ordering = []
            
            # Logic to handle the 'field,asc' or 'field,desc' format
            for i in range(0, len(fields), 2):
                field = fields[i]
                if i + 1 < len(fields):
                    direction = fields[i+1].lower()
                    if direction == 'desc':
                        field = f'-{field}'
                ordering.append(field)
            
            if ordering:
                return ordering

        return self.get_default_ordering(view)
