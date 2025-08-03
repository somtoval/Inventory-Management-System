from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Category, InventoryItem, StockTransaction, 
    Outlet, Sale, Purchase, SalesForecast
)

# =====================
# User & Authentication Serializers
# =====================
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
        read_only_fields = ('id', 'date_joined')

# =====================
# Category Serializers
# =====================
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

# =====================
# Inventory Serializers
# =====================
class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = '__all__'

    def get_is_low_stock(self, obj):
        return obj.quantity <= obj.min_quantity

class InventoryItemCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'

    def validate(self, attrs):
        if attrs.get('selling_price', 0) < attrs.get('cost_price', 0):
            raise serializers.ValidationError("Selling price cannot be less than cost price")
        return attrs

class StockTransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = StockTransaction
        fields = '__all__'
        read_only_fields = ('user', 'timestamp')

# =====================
# Outlet Serializers
# =====================
class OutletSerializer(serializers.ModelSerializer):
    total_sales = serializers.SerializerMethodField()

    class Meta:
        model = Outlet
        fields = '__all__'

    def get_total_sales(self, obj):
        return obj.sale_set.count()

# =====================
# Sales Serializers
# =====================
class SaleSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    outlet_name = serializers.CharField(source='outlet.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ('user', 'timestamp')

class SaleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ('outlet', 'item', 'quantity', 'total_price')

    def validate(self, attrs):
        item = attrs['item']
        quantity = attrs['quantity']
        
        if item.quantity < quantity:
            raise serializers.ValidationError(f"Insufficient stock. Available: {item.quantity}")
        
        expected_price = item.selling_price * quantity
        if abs(attrs['total_price'] - expected_price) > 0.01:
            raise serializers.ValidationError(f"Total price should be {expected_price}")
        
        return attrs

# =====================
# Purchase Serializers
# =====================
class PurchaseSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Purchase
        fields = '__all__'
        read_only_fields = ('user', 'purchase_date')

class PurchaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = ('item', 'quantity', 'supplier', 'cost')

# =====================
# Sales Forecast Serializers
# =====================
class SalesForecastSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = SalesForecast
        fields = '__all__'
        read_only_fields = ('created_at',)

# =====================
# Dashboard Serializers
# =====================
class DashboardStatsSerializer(serializers.Serializer):
    total_inventory_items = serializers.IntegerField()
    low_stock_items = serializers.IntegerField()
    out_of_stock_items = serializers.IntegerField()
    today_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    today_sales_count = serializers.IntegerField()

class RecentSalesSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name')
    outlet_name = serializers.CharField(source='outlet.name')

    class Meta:
        model = Sale
        fields = ('id', 'item_name', 'outlet_name', 'quantity', 'total_price', 'timestamp')

# =====================
# Analytics Serializers
# =====================
class SalesAnalyticsSerializer(serializers.Serializer):
    period = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_quantity = serializers.IntegerField()
    sales_count = serializers.IntegerField()

class TopSellingItemSerializer(serializers.Serializer):
    item_name = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)