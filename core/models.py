
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Product(models.Model):
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, default="")
    brand = models.CharField(max_length=100, blank=True, default="")
    vehicle_fitment = models.CharField(max_length=255, blank=True, default="")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Dealer(models.Model):
    dealer_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    gstin = models.CharField(max_length=20, blank=True, default="")
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    def __str__(self):
        return f"{self.dealer_code} - {self.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("CONFIRMED", "Confirmed"),
        ("DISPATCHED", "Dispatched"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    order_number = models.CharField(max_length=30, unique=True)
    dealer = models.ForeignKey(
        Dealer, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="DRAFT"
    )
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    tax_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    line_tax = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    line_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_product_per_order",
            )
        ]
