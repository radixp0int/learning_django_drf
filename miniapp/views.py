from rest_framework import viewsets
from .models import Item
from .serializers import ItemSerializer
from core.pagination import StandardResultsSetPagination
from core.filters import CustomFilterBackend, CustomOrderingFilter
from rest_framework import filters

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [CustomFilterBackend, filters.SearchFilter, CustomOrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
