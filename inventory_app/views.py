from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db.models import Sum, Count
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction

from .models import (
    User, Category, InventoryItem, StockTransaction, 
    Outlet, Sale, Purchase, SalesForecast
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    CategorySerializer, InventoryItemSerializer, InventoryItemCreateUpdateSerializer,
    StockTransactionSerializer, OutletSerializer, SaleSerializer, SaleCreateSerializer,
    PurchaseSerializer, PurchaseCreateSerializer, SalesForecastSerializer,
    DashboardStatsSerializer, RecentSalesSerializer, SalesAnalyticsSerializer,
    TopSellingItemSerializer
)

# =====================
# Authentication Views
# =====================
class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'User created successfully',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

# =====================
# User Management Views (Manager Only)
# =====================
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_manager():
            return User.objects.all()
        return User.objects.filter(id=user.id)

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_manager():
            return User.objects.all()
        return User.objects.filter(id=user.id)

# =====================
# Category Views
# =====================
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

# =====================
# Inventory Views
# =====================
class InventoryItemListCreateView(generics.ListCreateAPIView):
    queryset = InventoryItem.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InventoryItemCreateUpdateSerializer
        return InventoryItemSerializer

    def get_queryset(self):
        queryset = InventoryItem.objects.select_related('category')
        
        # Filter parameters
        category = self.request.query_params.get('category')
        low_stock = self.request.query_params.get('low_stock')
        out_of_stock = self.request.query_params.get('out_of_stock')
        
        if category:
            queryset = queryset.filter(category__id=category)
        if low_stock == 'true':
            queryset = queryset.filter(quantity__lte=models.F('min_quantity'))
        if out_of_stock == 'true':
            queryset = queryset.filter(is_out_of_stock=True)
            
        return queryset

class InventoryItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InventoryItem.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return InventoryItemCreateUpdateSerializer
        return InventoryItemSerializer

# =====================
# Stock Transaction Views
# =====================
class StockTransactionListCreateView(generics.ListCreateAPIView):
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = StockTransaction.objects.select_related('item', 'user')
        
        item = self.request.query_params.get('item')
        transaction_type = self.request.query_params.get('type')
        
        if item:
            queryset = queryset.filter(item__id=item)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        with transaction.atomic():
            stock_transaction = serializer.save(user=self.request.user)
            item = stock_transaction.item
            
            if stock_transaction.transaction_type == 'in':
                item.quantity += stock_transaction.quantity
                item.is_out_of_stock = False
            else:  # stock out
                item.quantity -= stock_transaction.quantity
                if item.quantity <= 0:
                    item.is_out_of_stock = True
                    item.quantity = 0
            
            item.save()

class StockTransactionDetailView(generics.RetrieveAPIView):
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

# =====================
# Outlet Views
# =====================
class OutletListCreateView(generics.ListCreateAPIView):
    queryset = Outlet.objects.all()
    serializer_class = OutletSerializer
    permission_classes = [permissions.IsAuthenticated]

class OutletDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Outlet.objects.all()
    serializer_class = OutletSerializer
    permission_classes = [permissions.IsAuthenticated]

# =====================
# Sales Views
# =====================
class SaleListCreateView(generics.ListCreateAPIView):
    queryset = Sale.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SaleCreateSerializer
        return SaleSerializer

    def get_queryset(self):
        queryset = Sale.objects.select_related('item', 'outlet', 'user')
        
        outlet = self.request.query_params.get('outlet')
        item = self.request.query_params.get('item')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if outlet:
            queryset = queryset.filter(outlet__id=outlet)
        if item:
            queryset = queryset.filter(item__id=item)
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
            
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        with transaction.atomic():
            sale = serializer.save(user=self.request.user)
            item = sale.item
            
            # Update inventory
            item.quantity -= sale.quantity
            if item.quantity <= 0:
                item.is_out_of_stock = True
                item.quantity = 0
            item.save()
            
            # Create stock transaction
            StockTransaction.objects.create(
                item=item,
                transaction_type='out',
                quantity=sale.quantity,
                user=self.request.user
            )

class SaleDetailView(generics.RetrieveAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]

# =====================
# Purchase Views
# =====================
class PurchaseListCreateView(generics.ListCreateAPIView):
    queryset = Purchase.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PurchaseCreateSerializer
        return PurchaseSerializer

    def get_queryset(self):
        queryset = Purchase.objects.select_related('item', 'user')
        
        item = self.request.query_params.get('item')
        supplier = self.request.query_params.get('supplier')
        
        if item:
            queryset = queryset.filter(item__id=item)
        if supplier:
            queryset = queryset.filter(supplier__icontains=supplier)
            
        return queryset.order_by('-purchase_date')

    def perform_create(self, serializer):
        with transaction.atomic():
            purchase = serializer.save(user=self.request.user)
            item = purchase.item
            
            # Update inventory
            item.quantity += purchase.quantity
            item.is_out_of_stock = False
            item.save()
            
            # Create stock transaction
            StockTransaction.objects.create(
                item=item,
                transaction_type='in',
                quantity=purchase.quantity,
                user=self.request.user
            )

class PurchaseDetailView(generics.RetrieveAPIView):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

# =====================
# Sales Forecast Views
# =====================
class SalesForecastListCreateView(generics.ListCreateAPIView):
    queryset = SalesForecast.objects.all()
    serializer_class = SalesForecastSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = SalesForecast.objects.select_related('item')
        
        item = self.request.query_params.get('item')
        if item:
            queryset = queryset.filter(item__id=item)
            
        return queryset.order_by('-forecast_date')

class SalesForecastDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SalesForecast.objects.all()
    serializer_class = SalesForecastSerializer
    permission_classes = [permissions.IsAuthenticated]

# =====================
# Dashboard Views
# =====================
class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        
        # Calculate stats
        total_inventory_items = InventoryItem.objects.count()
        low_stock_items = InventoryItem.objects.filter(
            quantity__lte=models.F('min_quantity')
        ).count()
        out_of_stock_items = InventoryItem.objects.filter(is_out_of_stock=True).count()
        
        today_sales_data = Sale.objects.filter(timestamp__date=today).aggregate(
            total=Sum('total_price'),
            count=Count('id')
        )
        
        today_sales = today_sales_data['total'] or 0
        today_sales_count = today_sales_data['count'] or 0
        
        stats = {
            'total_inventory_items': total_inventory_items,
            'low_stock_items': low_stock_items,
            'out_of_stock_items': out_of_stock_items,
            'today_sales': today_sales,
            'today_sales_count': today_sales_count
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)

class RecentSalesView(generics.ListAPIView):
    serializer_class = RecentSalesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Sale.objects.select_related('item', 'outlet').order_by('-timestamp')[:10]

# =====================
# Analytics Views
# =====================
class SalesAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'daily')  # daily, weekly, monthly
        
        today = timezone.now().date()
        
        if period == 'daily':
            start_date = today - timedelta(days=30)
            sales = Sale.objects.filter(timestamp__date__gte=start_date)
        elif period == 'weekly':
            start_date = today - timedelta(weeks=12)
            sales = Sale.objects.filter(timestamp__date__gte=start_date)
        else:  # monthly
            start_date = today - timedelta(days=365)
            sales = Sale.objects.filter(timestamp__date__gte=start_date)
        
        analytics_data = sales.aggregate(
            total_sales=Sum('total_price'),
            total_quantity=Sum('quantity'),
            sales_count=Count('id')
        )
        
        analytics = {
            'period': period,
            'total_sales': analytics_data['total_sales'] or 0,
            'total_quantity': analytics_data['total_quantity'] or 0,
            'sales_count': analytics_data['sales_count'] or 0
        }
        
        serializer = SalesAnalyticsSerializer(analytics)
        return Response(serializer.data)

class TopSellingItemsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        
        top_items = Sale.objects.values('item__name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_quantity')[:limit]
        
        serializer = TopSellingItemSerializer(top_items, many=True)
        return Response(serializer.data)

# =====================
# Low Stock Alert View
# =====================
class LowStockItemsView(generics.ListAPIView):
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InventoryItem.objects.filter(
            quantity__lte=models.F('min_quantity')
        ).select_related('category')

# =====================
# Logout View
# =====================
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        















# Forecasting
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .forecast_service import SalesForecastService

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_ai_forecast(request):
    """
    Generate AI-powered forecast for a specific item
    """
    item_id = request.data.get('item_id')
    forecast_days = request.data.get('forecast_days', 30)
    
    if not item_id:
        return Response({'error': 'item_id is required'}, status=400)
    
    service = SalesForecastService()
    success, message = service.generate_forecast_for_item(item_id, forecast_days)
    
    if success:
        # Get the generated forecasts
        forecasts = SalesForecast.objects.filter(
            item_id=item_id,
            forecast_date__gte=timezone.now().date()
        ).order_by('forecast_date')
        
        serializer = SalesForecastSerializer(forecasts, many=True)
        return Response({
            'success': True,
            'message': message,
            'forecasts': serializer.data
        })
    else:
        return Response({'error': message}, status=400)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_all_forecasts(request):
    """
    Generate AI-powered forecasts for all items
    """
    if not request.user.is_manager():
        return Response({'error': 'Manager access required'}, status=403)
    
    forecast_days = request.data.get('forecast_days', 30)
    min_sales_threshold = request.data.get('min_sales_threshold', 5)
    
    service = SalesForecastService()
    results = service.generate_forecasts_for_all_items(forecast_days, min_sales_threshold)
    
    return Response({
        'success': True,
        'message': f'Generated forecasts for {len(results)} items',
        'results': results
    })