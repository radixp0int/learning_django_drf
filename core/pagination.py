from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'size'
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Customizing the response 'envelope' to match the requested standard format.
        """
        request = self.request
        sort_param = request.query_params.get('sort')
        
        # Determine sort information
        sort_info = {
            "default": True,
            "field": "created_at",
            "direction": "desc"
        }
        
        if sort_param:
            sort_info["default"] = False
            parts = [p.strip() for p in sort_param.split(',')]
            if parts:
                sort_info["field"] = parts[0]
                if len(parts) > 1:
                    sort_info["direction"] = parts[1].lower()
                else:
                    sort_info["direction"] = "asc"
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
                        sort_info["field"] = order[1:]
                        sort_info["direction"] = "desc"
                    else:
                        sort_info["field"] = order
                        sort_info["direction"] = "asc"

        return Response({
            "success": True,
            "timestamp": timezone.now().isoformat(),
            "data": {
                "content": data,
                "first": not self.page.has_previous(),
                "last": not self.page.has_next(),
                "page": {
                    "elements": len(data),
                    "number": self.page.number - 1,
                    "offset": self.page.start_index() - 1,
                    "size": self.get_page_size(request)
                },
                "total": {
                    "elements": self.page.paginator.count,
                    "pages": self.page.paginator.num_pages
                },
                "sort": sort_info
            },
            "message": "Data retrieved successfully.",
            "status": 200
        })
