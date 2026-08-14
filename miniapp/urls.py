from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FeedbackViewSet, ItemViewSet, ProductListView, TenantViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'tenants', TenantViewSet)
router.register(r'feedback', FeedbackViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('products/', ProductListView.as_view()),
]
