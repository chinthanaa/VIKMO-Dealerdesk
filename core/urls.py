
from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health),
    path("products/", views.products),
    path("products/<str:sku>/", views.product_detail),
    path("inventory/<str:sku>/", views.inventory),
    path("dealers/", views.dealers),
    path("dealers/<int:dealer_id>/", views.dealer_detail),

    # Orders — these views must be implemented in core/views.py
    path("orders/", views.orders),
    path("orders/<str:order_number>/", views.order_detail),
    path("orders/<str:order_number>/confirm/", views.confirm_order),
    path("orders/<str:order_number>/dispatch/", views.dispatch_order),
    path("orders/<str:order_number>/deliver/", views.deliver_order),
    path("orders/<str:order_number>/cancel/", views.cancel_order),

    # Supplier sync — this view must be implemented in core/views.py
    path("sync/supplier/", views.supplier_sync),
]



