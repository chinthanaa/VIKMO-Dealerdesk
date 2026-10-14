
from django.contrib import admin
from .models import Dealer, Product, Order, OrderItem

admin.site.register(Dealer)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
