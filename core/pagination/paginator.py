from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from core.ordering import describe, get_applied_ordering


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'size'
    max_page_size = 100

    def get_sort_info(self, request):
        """
        Build the envelope's 'sort' block.

        Prefers the ordering published by CustomOrderingFilter / ListDataMixin,
        which is what was *actually* applied — echoing the raw ?sort= parameter
        misreports any field the view rejected.
        """
        applied = get_applied_ordering(request)
        if applied is not None:
            fields = [describe(term) for term in applied['fields']]
            return {
                'default': applied['default'],
                'field': fields[0]['field'] if fields else None,
                'direction': fields[0]['direction'] if fields else None,
                'fields': fields,
            }

        return self.get_fallback_sort_info(request)

    def get_fallback_sort_info(self, request):
        """
        Best-effort guess for views that paginate without either ordering
        component. With no source of truth to consult, the raw parameter is the
        only signal available, so it is echoed as-is.
        """
        sort_param = request.query_params.get('sort')

        sort_info = {'default': True, 'field': 'created_at', 'direction': 'desc'}

        if sort_param:
            sort_info['default'] = False
            parts = [p.strip() for p in sort_param.split(',')]
            if parts:
                sort_info['field'] = parts[0]
                if len(parts) > 1:
                    sort_info['direction'] = parts[1].lower()
                else:
                    sort_info['direction'] = 'asc'
        else:
            # Attempt to get default ordering from the view
            view = request.parser_context.get('view') if request else None
            if view and hasattr(view, 'ordering'):
                default_ordering = view.ordering
                if isinstance(default_ordering, (list, tuple)) and default_ordering:
                    order = default_ordering[0]
                elif isinstance(default_ordering, str):
                    order = default_ordering
                else:
                    order = None

                if order:
                    if order.startswith('-'):
                        sort_info['field'] = order[1:]
                        sort_info['direction'] = 'desc'
                    else:
                        sort_info['field'] = order
                        sort_info['direction'] = 'asc'

        sort_info['fields'] = [{'field': sort_info['field'], 'direction': sort_info['direction']}]
        return sort_info

    def get_paginated_response(self, data):
        """
        Customizing the response 'envelope' to match the requested standard format.
        """
        request = self.request
        sort_info = self.get_sort_info(request)

        return Response(
            {
                'success': True,
                'timestamp': timezone.now().isoformat(),
                'data': {
                    'content': data,
                    'first': not self.page.has_previous(),
                    'last': not self.page.has_next(),
                    'page': {
                        'elements': len(data),
                        'number': self.page.number - 1,
                        'offset': self.page.start_index(),
                        'size': self.get_page_size(request),
                    },
                    'total': {
                        'elements': self.page.paginator.count,
                        'pages': self.page.paginator.num_pages,
                    },
                    'sort': sort_info,
                },
                'message': 'Data retrieved successfully.',
                'status': 200,
            }
        )
