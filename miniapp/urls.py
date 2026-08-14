from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FeedbackViewSet, ItemViewSet, ProductListView, TenantViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'tenants', TenantViewSet)
# analytics registers a Feedback viewset too — without explicit basenames both would
# derive 'feedback' and collide, leaving the reverse lookup to whichever loaded last.
router.register(r'feedback', FeedbackViewSet, basename='feedback')

urlpatterns = [
    path('', include(router.urls)),
    path('products/', ProductListView.as_view()),
]
