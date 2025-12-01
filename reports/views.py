"""
Reports app views - Sales reports, analytics, exports
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import json

from core.permissions import CanAccessReports
from pos.models import Sale, SaleItem, Payment
from catalog.models import Product, Category, InventoryAdjustment
from customers.models import Customer


def permission_required(request):
    """Check if user can access reports"""
    if not request.user.can_access_reports:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access reports.")
    return True


@login_required
def reports_dashboard(request):
    """Main reports dashboard"""
    permission_required(request)
    
    # Get date ranges
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's sales summary
    today_sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__date=today.date()
    ).aggregate(
        total=Sum('subtotal'),
        count=Count('id')
    )
    
    # Calculate average manually
    if today_sales['count'] and today_sales['count'] > 0 and today_sales['total']:
        today_sales['avg_transaction'] = today_sales['total'] / today_sales['count']
    else:
        today_sales['avg_transaction'] = Decimal('0.00')
    
    # This week's sales
    week_sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__gte=week_ago
    ).aggregate(
        total=Sum('subtotal'),
        count=Count('id')
    )
    
    # This month's sales
    month_sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED, 
        created_at__gte=month_ago
    ).aggregate(
        total=Sum('subtotal'),
        count=Count('id')
    )
    
    # Top selling products (last 30 days)
    top_products = SaleItem.objects.filter(
        sale__status=Sale.Status.COMPLETED,
        sale__created_at__gte=month_ago
    ).values(
        'product__name',
        'product__sku'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('line_total')
    ).order_by('-quantity_sold')[:10]
    
    # Recent sales
    recent_sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED
    ).select_related('cashier', 'customer').prefetch_related('items').order_by('-created_at')[:10]
    
    # Low stock products
    low_stock = Product.objects.filter(
        is_active=True,
        track_stock=True,
        stock__lte=F('low_stock_threshold')
    ).select_related('category')[:10]
    
    # Sales by payment method (last 30 days)
    payment_breakdown = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__gte=month_ago
    ).values('payment_method').annotate(
        count=Count('id'),
        total=Sum('subtotal')
    ).order_by('-total')
    
    # Top customers (last 30 days)
    top_customers = Customer.objects.annotate(
        total_spent=Sum('purchases__subtotal', filter=Q(
            purchases__status=Sale.Status.COMPLETED,
            purchases__created_at__gte=month_ago
        )),
        purchase_count=Count('purchases', filter=Q(
            purchases__status=Sale.Status.COMPLETED,
            purchases__created_at__gte=month_ago
        ))
    ).filter(total_spent__isnull=False).order_by('-total_spent')[:10]
    
    # Sales trend data for chart (last 7 days)
    daily_sales = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = timezone.make_aware(datetime.combine(day.date(), datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        
        day_data = Sale.objects.filter(
            status=Sale.Status.COMPLETED,
            created_at__gte=day_start,
            created_at__lt=day_end
        ).aggregate(
            total=Sum('subtotal'),
            count=Count('id')
        )
        
        daily_sales.append({
            'date': day.strftime('%a'),
            'total': float(day_data['total'] or 0),
            'count': day_data['count'] or 0
        })
    
    # Convert payment_breakdown to serializable format with readable labels
    payment_labels_map = {
        'cash': 'Cash',
        'card': 'Card',
        'momo': 'Mobile Money',
        'bank_transfer': 'Bank Transfer'
    }
    
    payment_data = []
    for item in payment_breakdown:
        payment_method_value = item['payment_method']
        payment_data.append({
            'payment_method': payment_labels_map.get(payment_method_value, payment_method_value.replace('_', ' ').title()),
            'count': item['count'],
            'total': float(item['total']) if item['total'] else 0
        })
    
    context = {
        'page_title': 'Reports Dashboard',
        'today_sales': today_sales,
        'week_sales': week_sales,
        'month_sales': month_sales,
        'top_products': top_products,
        'recent_sales': recent_sales,
        'low_stock': low_stock,
        'payment_breakdown': json.dumps(payment_data),
        'top_customers': top_customers,
        'daily_sales_json': json.dumps(daily_sales),
    }
    return render(request, 'reports/reports.html', context)


@login_required
def sales_report(request):
    """Sales report with date range filter"""
    permission_required(request)
    context = {'page_title': 'Sales Report'}
    return render(request, 'reports/sales_report.html', context)


@login_required
def product_report(request):
    """Product performance report"""
    permission_required(request)
    context = {'page_title': 'Product Report'}
    return render(request, 'reports/product_report.html', context)


@login_required
def customer_report(request):
    """Customer analytics report"""
    permission_required(request)
    context = {'page_title': 'Customer Report'}
    return render(request, 'reports/customer_report.html', context)


@login_required
def inventory_report(request):
    """Inventory status and movement report"""
    permission_required(request)
    context = {'page_title': 'Inventory Report'}
    return render(request, 'reports/inventory_report.html', context)


@login_required
def export_sales_csv(request):
    """Export sales data to CSV"""
    permission_required(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['Reference', 'Date', 'Customer', 'Total'])
    return response


@login_required
def export_products_csv(request):
    """Export products to CSV"""
    permission_required(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['SKU', 'Name', 'Price', 'Stock'])
    return response


@login_required
def api_sales_chart_data(request):
    """API endpoint for sales chart data"""
    permission_required(request)
    return JsonResponse({'data': []})