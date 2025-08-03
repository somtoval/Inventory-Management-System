from django.db import models
from django.contrib.auth.models import AbstractUser

# =====================
# User & Roles
# =====================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def is_manager(self):
        return self.role == 'manager'

    def is_staff_member(self):
        return self.role == 'staff'


# =====================
# Inventory
# =====================
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50)  # e.g., kg, bottles, packs
    min_quantity = models.PositiveIntegerField(default=0)  # For low-stock alerts
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_out_of_stock = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class StockTransaction(models.Model):
    TRANSACTION_TYPE = (
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPE)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.item.name} - {self.quantity}"


# =====================
# Outlets
# =====================
class Outlet(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


# =====================
# Sales
# =====================
class Sale(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Sale - {self.item.name} - {self.quantity}"


# =====================
# Purchasing
# =====================
class Purchase(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    supplier = models.CharField(max_length=255, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Purchase - {self.item.name} - {self.quantity}"


# =====================
# Predictive Analysis Model Ready (Optional)
# =====================
class SalesForecast(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    predicted_quantity = models.PositiveIntegerField()
    forecast_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Forecast - {self.item.name} - {self.predicted_quantity}"
