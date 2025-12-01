from django.urls import path
from . import views


app_name = 'pos'

urlpatterns = [
    path('', views.pos_screen, name='pos_screen'),
    path('sales/', views.sales_list, name='sales_list'),
    path('sale/<str:reference>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:sale_id>/receipt/', views.print_receipt_by_id, name='print_receipt_by_id'),
    path('receipt/<str:reference>/', views.print_receipt, name='print_receipt'),
    # API endpoints
    path('api/validate-coupon/', views.validate_coupon, name='validate_coupon'),
    path('api/lookup-customer/', views.lookup_customer, name='lookup_customer'),
    path('api/check-stock/', views.check_stock, name='check_stock'),
    path('api/search-customers/', views.search_customers, name='search_customers'),
    path('api/get-product-price/', views.get_product_price, name='get_product_price'),
]