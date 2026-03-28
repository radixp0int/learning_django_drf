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
This ensures your frontend always receives a consistent structure (e.g., `content` instead of `results`).

**Replicate this code:**
```python
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'size'  # Allows frontend to request ?size=50
    max_page_size = 100

    def get_paginated_response(self, data):
        request = self.request
        sort_param = request.query_params.get('sort')

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
                sort_info["direction"] = parts[1].lower() if len(parts) > 1 else "asc"
        else:
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
                    "number": self.page.number - 1,   # 0-based page number
                    "offset": self.page.start_index(), # 1-based index of first item
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

### 3. Custom Sorting & Filtering (`core/filters.py`)
If your frontend uses `?sort=name,asc` instead of DRF's default `?ordering=-name`, use this translator.
Invalid sort fields are silently ignored via `remove_invalid_fields` to prevent database errors.

**Replicate this code:**
```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

class CustomFilterBackend(DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return super().filter_queryset(request, queryset, view)

class CustomOrderingFilter(OrderingFilter):
    ordering_param = 'sort'

    def get_ordering(self, request, queryset, view):
        """
        Translates 'field,asc' -> 'field' and 'field,desc' -> '-field'
        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            ordering = []
            for i in range(0, len(fields), 2):
                field = fields[i]
                if i + 1 < len(fields):
                    direction = fields[i+1].lower()
                    if direction == 'desc':
                        field = f'-{field}'
                valid = self.remove_invalid_fields(queryset, [field.lstrip('-')], view, request)
                if valid:
                    ordering.append(field)
            if ordering:
                return ordering
        return self.get_default_ordering(view)
```

---

## 🚀 How to use in a ViewSet

### Simple filtering (exact match on local fields)
When you only need exact matching on fields that live directly on the model, `filterset_fields` is sufficient:

```python
from rest_framework import viewsets, filters
from core.pagination import StandardResultsSetPagination
from core.filters import CustomFilterBackend, CustomOrderingFilter

class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [CustomFilterBackend, filters.SearchFilter, CustomOrderingFilter]
    filterset_fields = ['status', 'category']   # exact match only
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']
```

### Advanced filtering (partial match, FK traversal)
When you need `icontains`, `gte`/`lte`, or filtering across FK relationships (e.g. `feedback__tenant__name`),
define a `FilterSet` and point to it with `filterset_class`:

```python
import django_filters
from myapp.models import MyModel

class MyModelFilter(django_filters.FilterSet):
    # Local field — partial, case-insensitive match
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    # FK traversal — filters MyModel by a related model's field
    tenant_name = django_filters.CharFilter(field_name='feedback__tenant__name', lookup_expr='icontains')
    feedback_rating = django_filters.NumberFilter(field_name='feedback__rating', lookup_expr='exact')

    class Meta:
        model = MyModel
        fields = ['name', 'tenant_name', 'feedback_rating']

class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [CustomFilterBackend, filters.SearchFilter, CustomOrderingFilter]
    filterset_class = MyModelFilter   # use filterset_class, not filterset_fields
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
```

> **Note:** The query param name matches the `FilterSet` attribute name, not `field_name`.
> So `field_name='feedback__tenant__name'` with attribute `tenant_name` means the client sends `?tenant_name=Acme`.

---

## 💡 Frontend Cheat Sheet
With this pattern, your React components can always expect:
- **Pagination**: `?page=1&size=10`
- **Filtering**: `?name=chris` (partial match) or `?status=active` (exact match)
- **FK Traversal Filtering**: `?tenant_name=acme` (maps to `feedback__tenant__name`)
- **Searching**: `?search=term`
- **Sorting**: `?sort=field_name,asc` or `?sort=field_name,desc`
- **Response Shape**:
```json
{
  "success": true,
  "timestamp": "2026-03-27T00:00:00Z",
  "data": {
    "content": [...],
    "first": true,
    "last": false,
    "page": { "elements": 10, "number": 0, "offset": 1, "size": 10 },
    "total": { "elements": 42, "pages": 5 },
    "sort": { "default": false, "field": "name", "direction": "asc" }
  },
  "message": "Data retrieved successfully.",
  "status": 200
}
```
