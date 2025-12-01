from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Invoice, InvoiceItem, InvoicePayment
from customers.models import Customer
from catalog.models import Product
from pos.models import Sale, Payment
from core.models import SiteSettings


@login_required
def wholesale_dashboard(request):
    """Wholesale overview dashboard"""
    # Get date ranges
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    
    # Statistics
    total_invoices = Invoice.objects.count()
    pending_invoices = Invoice.objects.filter(payment_status__in=['unpaid', 'partial']).count()
    overdue_invoices = Invoice.objects.filter(payment_status='overdue').count()
    
    # Revenue stats
    total_revenue = Invoice.objects.filter(payment_status='paid').aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    outstanding_amount = Invoice.objects.filter(
        payment_status__in=['unpaid', 'partial', 'overdue']
    ).aggregate(
        total=Sum(F('total_amount') - F('amount_paid'))
    )['total'] or Decimal('0.00')
    
    # This month stats
    month_invoices = Invoice.objects.filter(issue_date__gte=this_month_start).count()
    month_revenue = Invoice.objects.filter(
        issue_date__gte=this_month_start,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Recent invoices
    recent_invoices = Invoice.objects.select_related('customer').order_by('-created_at')[:10]
    
    # Top customers
    top_customers = Customer.objects.filter(
        customer_type='wholesale',
        invoices__isnull=False
    ).annotate(
        total_spent=Sum('invoices__total_amount')
    ).order_by('-total_spent')[:5]
    
    context = {
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'total_revenue': total_revenue,
        'outstanding_amount': outstanding_amount,
        'month_invoices': month_invoices,
        'month_revenue': month_revenue,
        'recent_invoices': recent_invoices,
        'top_customers': top_customers,
        'site_settings': SiteSettings.get_settings(),
    }
    
    return render(request, 'wholesale/dashboard.html', context)


@login_required
def invoice_list(request):
    """List all invoices with filtering"""
    invoices = Invoice.objects.select_related('customer', 'created_by').all()
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)
    
    # Filter by customer
    customer_filter = request.GET.get('customer', '')
    if customer_filter:
        invoices = invoices.filter(customer_id=customer_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        invoices = invoices.filter(issue_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(issue_date__lte=date_to)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(invoices, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get customers for filter dropdown
    customers = Customer.objects.filter(customer_type='wholesale')
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'customer_filter': customer_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'customers': customers,
        'site_settings': SiteSettings.get_settings(),
    }
    
    return render(request, 'wholesale/invoice_list.html', context)


@login_required
def invoice_detail(request, invoice_id):
    """View invoice details"""
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer', 'sale', 'created_by')
        .prefetch_related('items__product', 'invoice_payments__payment'),
        id=invoice_id
    )
    
    context = {
        'invoice': invoice,
        'site_settings': SiteSettings.get_settings(),
    }
    
    return render(request, 'wholesale/invoice_detail.html', context)


@login_required
def invoice_create(request):
    """Create a new invoice manually"""
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer_id')
            customer = get_object_or_404(Customer, id=customer_id)
            
            payment_terms = request.POST.get('payment_terms', 'net_30')
            notes = request.POST.get('notes', '')
            
            # Calculate totals
            subtotal = Decimal('0.00')
            tax_amount = Decimal('0.00')
            discount_amount = Decimal(request.POST.get('discount_amount', '0.00'))
            
            # Create invoice
            invoice = Invoice.objects.create(
                customer=customer,
                payment_terms=payment_terms,
                subtotal=subtotal,  # Will update after adding items
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=subtotal,
                notes=notes,
                created_by=request.user
            )
            
            # Add invoice items
            product_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')
            
            for i, product_id in enumerate(product_ids):
                if product_id:
                    product = get_object_or_404(Product, id=product_id)
                    quantity = int(quantities[i])
                    unit_price = Decimal(unit_prices[i])
                    
                    item = InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        description=product.name,
                        quantity=quantity,
                        unit_price=unit_price,
                        tax_rate=product.tax_rate
                    )
                    
                    subtotal += item.subtotal
                    tax_amount += item.tax_amount
            
            # Update invoice totals
            invoice.subtotal = subtotal
            invoice.tax_amount = tax_amount
            invoice.total_amount = subtotal + tax_amount - discount_amount
            invoice.save()
            
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully!')
            return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
            
        except Exception as e:
            messages.error(request, f'Error creating invoice: {str(e)}')
            return redirect('wholesale:invoice_create')
    
    # GET request
    customers = Customer.objects.filter(customer_type='wholesale')
    products = Product.objects.filter(stock__gt=0)
    
    context = {
        'customers': customers,
        'products': products,
        'site_settings': SiteSettings.get_settings(),
    }
    
    return render(request, 'wholesale/invoice_create.html', context)


@login_required
def invoice_from_sale(request, sale_id):
    """Generate invoice from existing sale"""
    sale = get_object_or_404(
        Sale.objects.select_related('customer').prefetch_related('items__product'),
        id=sale_id
    )
    
    # Check if invoice already exists
    if hasattr(sale, 'invoice'):
        messages.warning(request, 'Invoice already exists for this sale!')
        return redirect('wholesale:invoice_detail', invoice_id=sale.invoice.id)
    
    try:
        # Create invoice from sale
        invoice = Invoice.objects.create(
            customer=sale.customer,
            sale=sale,
            payment_terms='net_30',
            subtotal=sale.subtotal,
            tax_amount=sale.tax,
            discount_amount=sale.discount,
            total_amount=sale.total,
            amount_paid=sale.amount_paid,
            created_by=request.user
        )
        
        # Add invoice items from sale items
        for sale_item in sale.items.all():
            InvoiceItem.objects.create(
                invoice=invoice,
                product=sale_item.product,
                description=sale_item.product.name,
                quantity=sale_item.quantity,
                unit_price=sale_item.unit_price,
                discount=sale_item.discount,
                tax_rate=sale_item.tax_rate
            )
        
        # Link existing payments
        for payment in sale.payments.all():
            InvoicePayment.objects.create(
                invoice=invoice,
                payment=payment,
                amount=payment.amount,
                recorded_by=request.user
            )
        
        messages.success(request, f'Invoice {invoice.invoice_number} created from sale!')
        return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
        
    except Exception as e:
        messages.error(request, f'Error creating invoice: {str(e)}')
        return redirect('pos:sale_detail', reference=sale.reference)


@login_required
def invoice_print(request, invoice_id):
    """Print invoice"""
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer', 'created_by')
        .prefetch_related('items__product'),
        id=invoice_id
    )
    
    context = {
        'invoice': invoice,
        'site_settings': SiteSettings.get_settings(),
    }
    
    return render(request, 'wholesale/invoice_print.html', context)


@login_required
def invoice_record_payment(request, invoice_id):
    """Record payment against invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            payment_method = request.POST.get('payment_method', 'cash')
            notes = request.POST.get('notes', '')
            
            if amount <= 0:
                messages.error(request, 'Payment amount must be greater than zero!')
                return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
            
            if amount > invoice.balance_due:
                messages.error(request, 'Payment amount exceeds balance due!')
                return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
            
            # Create payment record
            payment = Payment.objects.create(
                sale=invoice.sale if invoice.sale else None,
                method=payment_method,
                amount=amount,
                amount_tendered=amount,
                change_amount=Decimal('0.00')
            )
            
            # Link payment to invoice
            InvoicePayment.objects.create(
                invoice=invoice,
                payment=payment,
                amount=amount,
                notes=notes,
                recorded_by=request.user
            )
            
            messages.success(request, f'Payment of {amount} recorded successfully!')
            return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
            
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
            return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
    
    return redirect('wholesale:invoice_detail', invoice_id=invoice.id)


@login_required
def invoice_cancel(request, invoice_id):
    """Cancel an invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if request.method == 'POST':
        if invoice.amount_paid > 0:
            messages.error(request, 'Cannot cancel invoice with payments!')
            return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
        
        invoice.payment_status = 'cancelled'
        invoice.save()
        
        messages.success(request, f'Invoice {invoice.invoice_number} cancelled successfully!')
        return redirect('wholesale:invoice_list')
    
    return redirect('wholesale:invoice_detail', invoice_id=invoice.id)
