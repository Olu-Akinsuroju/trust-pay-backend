from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.MerchantDashboardView.as_view(), name='merchant-dashboard'),
    path('deals/', views.MerchantDealsView.as_view(), name='merchant-deals'),
    path('deals/<slug:slug>/', views.MerchantDealDetailView.as_view(), name='merchant-deal-detail'),
    path('transactions/', views.MerchantTransactionsView.as_view(), name='merchant-transactions'),
    path('links/', views.PaymentLinkListView.as_view(), name='merchant-links'),
]
