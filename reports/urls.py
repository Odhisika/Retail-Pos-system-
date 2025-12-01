from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='dashboard'),
    path('sales/', views.sales_report, name='sales'),
    path('products/', views.product_report, name='products'),
    path('customers/', views.customer_report, name='customers'),
    path('inventory/', views.inventory_report, name='inventory'),
    
    # Exports
    path('export/sales/csv/', views.export_sales_csv, name='export_sales_csv'),
    path('export/products/csv/', views.export_products_csv, name='export_products_csv'),
    
    # API endpoints
    path('api/sales-chart/', views.api_sales_chart_data, name='api_sales_chart'),
]