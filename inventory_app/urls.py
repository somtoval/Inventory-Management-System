from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

# Main URL patterns
urlpatterns = [
    # =====================
    # Authentication URLs
    # =====================
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('auth/login/', views.UserLoginView.as_view(), name='user-login'),
    path('auth/logout/', views.LogoutView.as_view(), name='user-logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/profile/', views.UserProfileView.as_view(), name='user-profile'),
    
    # =====================
    # User Management URLs (Manager only)
    # =====================
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # =====================
    # Category URLs
    # =====================
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # =====================
    # Inventory URLs
    # =====================
    path('inventory/', views.InventoryItemListCreateView.as_view(), name='inventory-list-create'),
    path('inventory/<int:pk>/', views.InventoryItemDetailView.as_view(), name='inventory-detail'),
    path('inventory/low-stock/', views.LowStockItemsView.as_view(), name='low-stock-items'),
    
    # =====================
    # Stock Transaction URLs
    # =====================
    path('stock-transactions/', views.StockTransactionListCreateView.as_view(), name='stock-transaction-list-create'),
    path('stock-transactions/<int:pk>/', views.StockTransactionDetailView.as_view(), name='stock-transaction-detail'),
    
    # =====================
    # Outlet URLs
    # =====================
    path('outlets/', views.OutletListCreateView.as_view(), name='outlet-list-create'),
    path('outlets/<int:pk>/', views.OutletDetailView.as_view(), name='outlet-detail'),
    
    # =====================
    # Sales URLs
    # =====================
    path('sales/', views.SaleListCreateView.as_view(), name='sale-list-create'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale-detail'),
    
    # =====================
    # Purchase URLs
    # =====================
    path('purchases/', views.PurchaseListCreateView.as_view(), name='purchase-list-create'),
    path('purchases/<int:pk>/', views.PurchaseDetailView.as_view(), name='purchase-detail'),
    
    # =====================
    # Sales Forecast URLs
    # =====================
    path('forecasts/', views.SalesForecastListCreateView.as_view(), name='forecast-list-create'),
    path('forecasts/<int:pk>/', views.SalesForecastDetailView.as_view(), name='forecast-detail'),
    
    # AI Forecast URLs
    path('forecasts/generate/', views.generate_ai_forecast, name='generate-ai-forecast'),
    path('forecasts/generate-all/', views.generate_all_forecasts, name='generate-all-forecasts'),
    
    # =====================
    # Dashboard URLs
    # =====================
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/recent-sales/', views.RecentSalesView.as_view(), name='recent-sales'),
    
    # =====================
    # Analytics URLs
    # =====================
    path('analytics/sales/', views.SalesAnalyticsView.as_view(), name='sales-analytics'),
    path('analytics/top-selling/', views.TopSellingItemsView.as_view(), name='top-selling-items'),
]

# API Documentation (optional)
# Add these if you want to include API schema/documentation
"""
from rest_framework.schemas import get_schema_view
from rest_framework.renderers import JSONOpenAPIRenderer

schema_view = get_schema_view(
    title='Hotel Inventory Management API',
    description='API for managing hotel inventory, sales, and analytics',
    version='1.0.0',
    renderer_classes=[JSONOpenAPIRenderer],
)

urlpatterns += [
    path('schema/', schema_view, name='api-schema'),
]
"""