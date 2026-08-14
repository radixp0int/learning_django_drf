from rest_framework import filters, viewsets

from core.filtering.backends import CustomFilterBackend, CustomOrderingFilter
from core.pagination.paginator import StandardResultsSetPagination

from .models import Feedback
from .serializers import FeedbackSerializer


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer

    # Reusing the standardized pagination and filtering
    pagination_class = StandardResultsSetPagination
    filter_backends = [CustomFilterBackend, filters.SearchFilter, CustomOrderingFilter]

    # Specific filtering for this view
    filterset_fields = ['rating', 'is_resolved']
    search_fields = ['user_email', 'content']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
