from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FeedbackViewSet

router = DefaultRouter()
# Explicit basename: miniapp also registers a Feedback viewset, and both would
# otherwise derive 'feedback' from the model name and clobber each other's URL names.
router.register(r'feedback', FeedbackViewSet, basename='analytics-feedback')

urlpatterns = [
    path('', include(router.urls)),
]
