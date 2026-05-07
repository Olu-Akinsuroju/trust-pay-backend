from django.urls import path
from . import views

urlpatterns = [
    path('disputes/', views.DisputeListView.as_view(), name='admin-dispute-list'),
    path('disputes/<uuid:pk>/resolve/', views.DisputeResolveView.as_view(), name='admin-dispute-resolve'),
]
