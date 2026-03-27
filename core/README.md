# Django DRF Core Pattern

This directory contains standardized utilities to ensure a consistent API experience between your Django backend and your React/Frontend applications.

## 🎯 Goal
To provide a consistent "JSON Envelope" and query parameter syntax (sorting, filtering, pagination) across all API endpoints, reducing the amount of custom code needed in your ViewSets.

---

## 🛠 Setup Steps for New Projects

### 1. Create the `core` App
Always start by creating a dedicated app for shared utilities.
```bash
python manage.py startapp core
```
Add `'core'` to your `INSTALLED_APPS` in `settings.py`.

### 2. Standardize Pagination (`core/pagination.py`)
This ensures your frontend always receives a consistent structure (e.g., `items` instead of `results`).

**Replicate this code:**
```python
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'size' # Allows frontend to request ?size=50
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
```

### 3. Custom Sorting Syntax (`core/filters.py`)
If your frontend uses `?sort=name,asc` instead of DRF's default `?ordering=-name`, use this translator.

**Replicate this code:**
```python
from rest_framework.filters import OrderingFilter

class CustomOrderingFilter(OrderingFilter):
    ordering_param = 'sort' # Changes ?ordering= to ?sort=

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            ordering = []
            for i in range(0, len(fields), 2):
                field = fields[i]
                if i + 1 < len(fields):
                    direction = fields[i+1].lower()
                    if direction == 'desc':
                        field = f'-{field}' # Django's internal descending syntax
                ordering.append(field)
            return ordering
        return self.get_default_ordering(view)
```

---

## 🚀 How to use in a ViewSet

Once your `core` utilities are ready, using them in any new app is simple. Just import and reference them.

**Example: `myapp/views.py`**
```python
from rest_framework import viewsets, filters
from core.pagination import StandardResultsSetPagination
from core.filters import CustomOrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer

    # 1. Use the shared pagination
    pagination_class = StandardResultsSetPagination

    # 2. Use the shared filter backends
    filter_backends = [
        DjangoFilterBackend,    # For ?status=done
        filters.SearchFilter,   # For ?search=keyword
        CustomOrderingFilter    # For ?sort=date,desc
    ]

    # 3. Define the specific fields for this model
    filterset_fields = ['status', 'category']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
```

## 💡 Frontend Cheat Sheet
With this pattern, your React components can always expect:
- **Pagination**: `?page=1&size=10`
- **Filtering**: `?field_name=value`
- **Searching**: `?search=term`
- **Sorting**: `?sort=field_name,asc` or `?sort=field_name,desc`
- **Response Shape**: `{ success: true, data: { content: [...], page: {...}, total: {...}, sort: {...} }, message: "...", status: 200 }`
