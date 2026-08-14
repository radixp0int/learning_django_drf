import django_filters
from rest_framework import filters, generics, viewsets

from core.filtering.backends import CustomFilterBackend, CustomOrderingFilter
from core.filtering.mixins import ListDataMixin
from core.pagination.paginator import StandardResultsSetPagination

from .models import Feedback, Item, Tenant
from .serializers import FeedbackSerializer, ItemSerializer, TenantSerializer


class ItemFilter(django_filters.FilterSet):
    # The feedback_* filters traverse the reverse FK (Item -> many Feedback), so the
    # join emits one row per matching Feedback. distinct=True dedupes them; django-filter
    # only applies it when the filter actually receives a value, so unfiltered list
    # requests pay nothing for it.
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    feedback_content = django_filters.CharFilter(
        field_name='feedback__content', lookup_expr='icontains', distinct=True
    )
    feedback_rating = django_filters.NumberFilter(
        field_name='feedback__rating', lookup_expr='exact', distinct=True
    )
    feedback_tenant_name = django_filters.CharFilter(
        field_name='feedback__tenant__name', lookup_expr='icontains', distinct=True
    )

    class Meta:
        model = Item
        fields = ['name', 'feedback_content', 'feedback_rating', 'feedback_tenant_name']


class FeedbackFilter(django_filters.FilterSet):
    content = django_filters.CharFilter(field_name='content', lookup_expr='icontains')
    rating = django_filters.NumberFilter(field_name='rating', lookup_expr='exact')
    item_name = django_filters.CharFilter(field_name='item__name', lookup_expr='icontains')
    tenant_name = django_filters.CharFilter(field_name='tenant__name', lookup_expr='icontains')

    class Meta:
        model = Feedback
        fields = ['content', 'rating', 'item_name', 'tenant_name']


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [CustomFilterBackend, filters.SearchFilter, CustomOrderingFilter]
    filterset_class = ItemFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [CustomFilterBackend, CustomOrderingFilter]
    filterset_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('item', 'tenant').all()
    serializer_class = FeedbackSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [CustomFilterBackend, filters.SearchFilter, CustomOrderingFilter]
    filterset_class = FeedbackFilter
    search_fields = ['content', 'item__name', 'tenant__name']
    ordering_fields = ['rating', 'created_at', 'item__name', 'tenant__name']
    ordering = ['-created_at']


# ---------------------------------------------------------------------------
# Non-model example — static/external data, no ORM queryset involved
# ---------------------------------------------------------------------------

STATIC_PRODUCTS = [
    {'id': 1, 'name': 'Widget Pro', 'category': 'hardware', 'price': 99.99, 'in_stock': True},
    {'id': 2, 'name': 'Gadget Basic', 'category': 'hardware', 'price': 29.99, 'in_stock': True},
    {
        'id': 3,
        'name': 'Doohickey Ultra',
        'category': 'software',
        'price': 149.99,
        'in_stock': False,
    },
    {'id': 4, 'name': 'Thingamajig Lite', 'category': 'software', 'price': 49.99, 'in_stock': True},
    {'id': 5, 'name': 'Gizmo Standard', 'category': 'hardware', 'price': 79.99, 'in_stock': True},
    {'id': 6, 'name': 'Contraption X', 'category': 'software', 'price': 199.99, 'in_stock': False},
    {'id': 7, 'name': 'Device Alpha', 'category': 'hardware', 'price': 59.99, 'in_stock': True},
    {'id': 8, 'name': 'Unit Omega', 'category': 'software', 'price': 89.99, 'in_stock': True},
    {'id': 9, 'name': 'Module Core', 'category': 'hardware', 'price': 39.99, 'in_stock': False},
    {
        'id': 10,
        'name': 'Component Elite',
        'category': 'software',
        'price': 249.99,
        'in_stock': True,
    },
]


class ProductListView(ListDataMixin, generics.GenericAPIView):
    """
    Example view backed by a plain list (no model / no ORM).
    Supports ?name=, ?category=, ?sort=field,asc|desc, ?page=, ?size=
    """

    pagination_class = StandardResultsSetPagination
    filterable_fields = ['name', 'category']
    sortable_fields = ['name', 'price', 'category']
    default_ordering = ('name', 'asc')

    def get(self, request):
        data = list(STATIC_PRODUCTS)
        data = self.filter_list(data, request)
        data = self.sort_list(data, request)
        return self.get_paginated_list(data, request)
