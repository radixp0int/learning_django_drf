from rest_framework.response import Response

from core.ordering import set_applied_ordering


class ListDataMixin:
    """
    Mixin for views that serve plain Python lists instead of Django ORM querysets.

    Provides filter_list() and sort_list() helpers that honour the same query
    parameter conventions as the ORM-backed backends:
      - Filtering : ?field=value      (icontains, case-insensitive)
      - Sorting   : ?sort=field,asc   or  ?sort=field,desc
      - Pagination: ?page=1&size=10   (handled by StandardResultsSetPagination)

    Usage in a view:

        class MyView(ListDataMixin, generics.GenericAPIView):
            pagination_class = StandardResultsSetPagination
            filterable_fields = ['name', 'status']
            sortable_fields   = ['name', 'created_at']
            default_ordering  = ('name', 'asc')

            def get(self, request):
                data = fetch_from_somewhere()          # list of dicts
                data = self.filter_list(data, request)
                data = self.sort_list(data, request)
                return self.get_paginated_list(data, request)
    """

    # Declare which fields can be filtered/sorted by the client.
    filterable_fields = []
    sortable_fields = []
    # Tuple of (field, direction) used when no ?sort= param is present.
    default_ordering = None  # e.g. ('name', 'asc') or ('created_at', 'desc')

    def filter_list(self, data, request):
        """
        For each field in filterable_fields, checks ?field=value and keeps
        only items where the value appears anywhere in the field (icontains).
        """
        for field in self.filterable_fields:
            value = request.query_params.get(field)
            if value:
                data = [item for item in data if value.lower() in str(item.get(field, '')).lower()]
        return data

    def sort_list(self, data, request):
        """
        Reads ?sort=field,asc or ?sort=field,desc and sorts the list.
        Falls back to default_ordering when no sort param is provided.
        Fields not listed in sortable_fields are silently ignored.

        Publishes the resolved ordering via core.ordering so the paginator
        reports default_ordering correctly — it can't read it off the view the
        way it reads `ordering` off an ORM view.
        """
        sort_param = request.query_params.get('sort')
        is_default = True

        if sort_param:
            parts = [p.strip() for p in sort_param.split(',')]
            field = parts[0]
            direction = parts[1].lower() if len(parts) > 1 else 'asc'
            is_default = False
        elif self.default_ordering:
            field, direction = self.default_ordering
        else:
            set_applied_ordering(request, [], is_default=True)
            return data

        if self.sortable_fields and field not in self.sortable_fields:
            # Invalid field — fall back to default_ordering if set
            if self.default_ordering:
                field, direction = self.default_ordering
                is_default = True
            else:
                set_applied_ordering(request, [], is_default=True)
                return data

        reverse = direction == 'desc'
        set_applied_ordering(request, [f'-{field}' if reverse else field], is_default=is_default)
        data = sorted(
            data, key=lambda item: (item.get(field) is None, item.get(field, '')), reverse=reverse
        )
        return data

    def get_paginated_list(self, data, request):
        """
        Runs data through the view's pagination_class (same as ORM views).
        Returns a paginated Response or a plain Response if pagination is off.
        """
        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(data)
