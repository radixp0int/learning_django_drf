from rest_framework import viewsets, filters
from .models import Feedback
from .serializers import FeedbackSerializer
from core.pagination import StandardResultsSetPagination
from core.filters import CustomFilterBackend, CustomOrderingFilter

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
