from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatasetViewSet, CustomAuthToken

router = DefaultRouter()
router.register(r'datasets', DatasetViewSet, basename='dataset')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', CustomAuthToken.as_view(), name='api_token_auth'),
]