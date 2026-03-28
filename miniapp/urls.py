from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, TenantViewSet, FeedbackViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'tenants', TenantViewSet)
router.register(r'feedback', FeedbackViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
