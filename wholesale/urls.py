from django.urls import path
from . import views

app_name = 'wholesale'

urlpatterns = [
    # Dashboard
    path('', views.wholesale_dashboard, name='dashboard'),
    
    # Invoice URLs
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/print/', views.invoice_print, name='invoice_print'),
    path('invoices/<int:invoice_id>/payment/', views.invoice_record_payment, name='invoice_record_payment'),
    path('invoices/<int:invoice_id>/cancel/', views.invoice_cancel, name='invoice_cancel'),
    path('sales/<int:sale_id>/create-invoice/', views.invoice_from_sale, name='invoice_from_sale'),
]
