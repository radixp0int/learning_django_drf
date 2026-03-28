from rest_framework import viewsets
from .models import Item, Tenant, Feedback
from .serializers import ItemSerializer, TenantSerializer, FeedbackSerializer
from core.pagination import StandardResultsSetPagination
from core.filters import CustomFilterBackend, CustomOrderingFilter
from rest_framework import filters
import django_filters

class ItemFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    feedback_content = django_filters.CharFilter(field_name='feedback__content', lookup_expr='icontains')
    feedback_rating = django_filters.NumberFilter(field_name='feedback__rating', lookup_expr='exact')
    feedback_tenant_name = django_filters.CharFilter(field_name='feedback__tenant__name', lookup_expr='icontains')

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
