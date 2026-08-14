# Django DRF Core Pattern

This directory contains standardized utilities to ensure a consistent API experience between your Django backend and your React/Frontend applications.

## 🎯 Goal
To provide a consistent "JSON Envelope" and query parameter syntax (sorting, filtering, pagination) across all API endpoints, reducing the amount of custom code needed in your ViewSets.

---

## 📁 Layout

```
core/
├── filtering/
│   ├── backends.py   # CustomFilterBackend, CustomOrderingFilter (?sort=field,dir)
│   └── mixins.py     # ListDataMixin — same contract for non-ORM data
├── pagination/
│   └── paginator.py  # StandardResultsSetPagination — the JSON envelope
└── tests/
```

> These were split out of the former flat `core/filters.py` and `core/pagination.py`.
> Update imports to `core.filtering.backends` and `core.pagination.paginator`.

For live endpoint examples and known gotchas, see the [root README](../README.md).

---

## 🛠 Setup Steps for New Projects

### 1. Create the `core` App
Always start by creating a dedicated app for shared utilities.
```bash
python manage.py startapp core
```
Add `'core'` to your `INSTALLED_APPS` in `settings.py`.

### 2. Publish the applied ordering (`core/ordering.py`)
The paginator runs *after* filtering and can't see what the ordering backend decided, so on its
own it can only guess by re-parsing the query string — which is wrong for any field the view
rejected, and wrong again for `ListDataMixin` views that have no `ordering` attribute. This tiny
module lets whoever resolves the ordering hand the answer forward.

Keep it at `core/` root: both `core/filtering/` and `core/pagination/` import it, and a neutral
module keeps that dependency acyclic.

**Replicate this code:**
```python
_ATTR = '_core_applied_ordering'


def set_applied_ordering(request, fields, is_default):
    """fields: ORM-style terms, e.g. ['-rating', 'created_at'].
    is_default: True when the view's default was used."""
    setattr(request, _ATTR, {'fields': list(fields or []), 'default': bool(is_default)})


def get_applied_ordering(request):
    """None means no ordering component ran — callers should fall back."""
    return getattr(request, _ATTR, None)


def describe(term):
    """'-rating' -> {'field': 'rating', 'direction': 'desc'}"""
    if term.startswith('-'):
        return {'field': term[1:], 'direction': 'desc'}
    return {'field': term, 'direction': 'asc'}
```

The DRF `Request` is the same object across `filter_queryset()` and `paginate_queryset()`, which
is what makes it a safe carrier.

### 3. Standardize Pagination (`core/pagination/paginator.py`)
This ensures your frontend always receives a consistent structure (e.g., `content` instead of `results`).

**Replicate this code:**
```python
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone

from core.ordering import describe, get_applied_ordering

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'size'  # Allows frontend to request ?size=50
    max_page_size = 100

    def get_sort_info(self, request):
        """Prefer the ordering that was actually applied over the raw ?sort= param."""
        applied = get_applied_ordering(request)
        if applied is not None:
            fields = [describe(term) for term in applied['fields']]
            return {
                "default": applied['default'],
                "field": fields[0]['field'] if fields else None,
                "direction": fields[0]['direction'] if fields else None,
                "fields": fields,
            }
        return self.get_fallback_sort_info(request)

    def get_fallback_sort_info(self, request):
        """Best-effort for views with neither ordering component: echo the param."""
        sort_param = request.query_params.get('sort')
        sort_info = {"default": True, "field": "created_at", "direction": "desc"}

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

        sort_info["fields"] = [{"field": sort_info["field"], "direction": sort_info["direction"]}]
        return sort_info

    def get_paginated_response(self, data):
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
                    "size": self.get_page_size(self.request)
                },
                "total": {
                    "elements": self.page.paginator.count,
                    "pages": self.page.paginator.num_pages
                },
                "sort": self.get_sort_info(self.request)
            },
            "message": "Data retrieved successfully.",
            "status": 200
        })
```

### 4. Custom Sorting & Filtering (`core/filtering/backends.py`)
If your frontend uses `?sort=name,asc` instead of DRF's default `?ordering=-name`, use this translator.
Invalid sort fields are silently ignored via `remove_invalid_fields` to prevent database errors.

**Replicate this code:**
```python
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
                set_applied_ordering(request, ordering, is_default=False)
                return ordering

        # No sort param, or every requested field was rejected as invalid.
        default_ordering = self.get_default_ordering(view)
        set_applied_ordering(request, default_ordering, is_default=True)
        return default_ordering
```

---

## 🚀 How to use in a ViewSet

### Simple filtering (exact match on local fields)
When you only need exact matching on fields that live directly on the model, `filterset_fields` is sufficient:

```python
from rest_framework import viewsets, filters
from core.pagination.paginator import StandardResultsSetPagination
from core.filtering.backends import CustomFilterBackend, CustomOrderingFilter

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

    # Reverse FK traversal (MyModel -> many Feedback). The join emits one row per
    # matching Feedback, so distinct=True is required to avoid duplicates and an
    # inflated total.elements. django-filter only applies it when the filter
    # receives a value, so unfiltered requests pay nothing for it.
    tenant_name = django_filters.CharFilter(
        field_name='feedback__tenant__name', lookup_expr='icontains', distinct=True
    )
    feedback_rating = django_filters.NumberFilter(
        field_name='feedback__rating', lookup_expr='exact', distinct=True
    )

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

> **Forward vs reverse matters.** A forward FK (`Feedback` -> `item`) is many-to-one and
> cannot multiply rows, so `distinct=True` is unnecessary there. Only traversals that fan out
> to *many* related rows need it.

### Non-model data (no ORM queryset)

DRF's filter backends require a queryset, so they can't touch data that comes from a
static list, an external API, a CSV, or a cache. `ListDataMixin` reimplements the same
query-parameter contract in plain Python so those endpoints stay consistent with the
ORM ones.

```python
from rest_framework import generics
from core.filtering.mixins import ListDataMixin
from core.pagination.paginator import StandardResultsSetPagination

class ProductListView(ListDataMixin, generics.GenericAPIView):
    pagination_class  = StandardResultsSetPagination
    filterable_fields = ['name', 'category']      # each becomes ?name= / ?category=
    sortable_fields   = ['name', 'price', 'category']
    default_ordering  = ('name', 'asc')           # used when no ?sort= is sent

    def get(self, request):
        data = list(STATIC_PRODUCTS)              # or requests.get(...).json()
        data = self.filter_list(data, request)
        data = self.sort_list(data, request)
        return self.get_paginated_list(data, request)
```

Inherit from `generics.GenericAPIView` (not `APIView`) — the mixin's
`get_paginated_list()` calls `paginate_queryset()` / `get_paginated_response()`,
which only `GenericAPIView` provides.

**Deliberate limits of the list implementation:**

| | ORM backends | `ListDataMixin` |
|---|---|---|
| Multi-field sort | yes | **single field only** |
| `?search=` | via `SearchFilter` | not implemented |
| Filter matching | per-`FilterSet` | always `icontains` |
| Unknown sort field | dropped, default applies | dropped, `default_ordering` applies |
| `None` values | DB collation decides | always sorted last |

`sort_list()` publishes the ordering it resolved via `core.ordering.set_applied_ordering()`,
and the paginator reads it back when building the envelope. Without that, the `sort` block
would fall back to reading `view.ordering` — an attribute `ListDataMixin` views don't define —
and misreport the default on an endpoint that may have no `created_at` field at all.

---

## ⚠️ Multi-valued relations and `ordering_fields`

`distinct=True` fixes duplicates on the **filter** path. The **ordering** path has a separate,
unfixed hazard that this pattern inherits directly from DRF.

Ordering across a multi-valued relation adds a JOIN that multiplies rows. Stock
`rest_framework.filters.OrderingFilter`, with no filtering applied at all:

```
?ordering=feedback__content  ->  51 rows, 20 distinct items
```

Paginated, it silently loses records — Django strips `ORDER BY` when building a `COUNT`, so the
count and the fetch disagree (`count()` -> 20, `len(list(qs))` -> 51). The paginator trusts the
count, reports 2 pages, and walking every page yields 20 rows covering only **14** distinct
items: 6 are unreachable through the API.

DRF guards `SearchFilter` against this with `must_call_distinct()` -> an `Exists()` subquery.
`OrderingFilter` has no equivalent — every `distinct`-related line in `rest_framework/filters.py`
is in `SearchFilter`.

**Rule:** keep reverse-relation paths out of `ordering_fields`. Forward FKs are fine —
`ordering_fields = ['item__name', 'tenant__name']` on a `Feedback` viewset is safe because
many-to-one cannot multiply rows. The distinction is the direction of the relation, not the
presence of `__`.

Sorting on a joined column also defeats `distinct=True`, because `SELECT DISTINCT` adds the
`ORDER BY` column to the SELECT list — rows differing only in that column stop being duplicates.
The same rule avoids it.

---

## 💡 Frontend Cheat Sheet
With this pattern, your React components can always expect:
- **Pagination**: `?page=1&size=10`
- **Filtering**: `?name=chris` (partial match) or `?status=active` (exact match)
- **FK Traversal Filtering**: `?tenant_name=acme` (maps to `feedback__tenant__name`)
- **Searching**: `?search=term`
- **Sorting**: `?sort=field_name,asc` or `?sort=field_name,desc` (multi: `?sort=a,asc,b,desc`)
- **Sort feedback**: `data.sort` reports the ordering *actually applied*, with every term
  under `data.sort.fields` — a rejected field shows the default that took effect instead
- **Caveats**: `?ordering=` is inert (param is `sort`); `size` caps at 100; an out-of-range
  `page` returns a bare `404 {"detail": "Invalid page."}`; only *list* responses are enveloped
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
    "sort": {
      "default": false,
      "field": "name",
      "direction": "asc",
      "fields": [ { "field": "name", "direction": "asc" } ]
    }
  },
  "message": "Data retrieved successfully.",
  "status": 200
}
```
