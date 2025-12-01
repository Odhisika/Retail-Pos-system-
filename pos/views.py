from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import IsCashier
from .models import Sale, SaleItem, Payment
from .serializers import SaleSerializer, CreateSaleSerializer
from catalog.models import Product, Category
from customers.models import Customer
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from core.models import SiteSettings
from django.views.decorators.http import require_http_methods
import json
from catalog.models import Coupon


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related('cashier', 'customer').prefetch_related('items', 'payments').all()
    serializer_class = SaleSerializer
    permission_classes = [IsCashier]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'cashier', 'customer', 'payment_method']
    
    @transaction.atomic
    @action(detail=False, methods=['post'])
    def create_sale(self, request):
        """Create a complete sale with items and payments"""
        serializer = CreateSaleSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Create Sale Validation Errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Get or create customer based on phone number
        customer_phone = data.get('customer_phone')
        customer_name = data.get('customer_name')
        customer_email = data.get('customer_email', '')
        
        customer, created = Customer.objects.get_or_create(
            phone=customer_phone,
            defaults={
                'name': customer_name,
                'email': customer_email,
                'is_active': True
            }
        )
        
        # Update customer details if they already existed
        if not created:
            customer.name = customer_name
            if customer_email:
                customer.email = customer_email
            customer.save()
        
        # Create sale
        sale = Sale.objects.create(
            cashier=request.user,
            customer=customer,
            discount=data.get('discount', 0),
            notes=data.get('notes', ''),
            terminal_id=request.user.terminal_id
        )
        
        # Create sale items
        for item_data in data['items']:
            product = Product.objects.get(id=item_data['product_id'])
            
            if not product.can_sell(item_data['quantity']):
                return Response(
                    {'error': f'Product {product.sku} cannot be sold'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine price based on customer type
            unit_price, _ = product.get_price_for_customer(customer, item_data['quantity'])
            
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=item_data['quantity'],
                unit_price=unit_price,
                tax_rate=product.tax_rate,
                discount=item_data.get('discount', 0)
            )
        
        # Calculate totals
        sale.calculate_totals()
        
        # Create payments
        total_payment = 0
        for payment_data in data['payments']:
            amount = Decimal(str(payment_data['amount']))
            total_payment += amount
            Payment.objects.create(
                sale=sale,
                amount=amount,
                method=payment_data['method'],
                status=Payment.Status.COMPLETED,
                amount_tendered=payment_data.get('amount_tendered'),
                change_amount=payment_data.get('change_amount')
            )

        # Validate payment based on customer type
        if customer.customer_type == 'wholesale':
            min_payment = sale.total * Decimal('0.5')
            if total_payment < min_payment:
                 return Response(
                    {'error': f'Wholesale customers must pay at least 50% ({min_payment})'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if total_payment < sale.total:
                sale.payment_status = Sale.PaymentStatus.PARTIAL
                sale.save()
                # Update customer balance
                remaining_balance = sale.total - total_payment
                customer.current_balance += remaining_balance
                customer.save()
        else:
            # Retail customers must pay full amount
            if total_payment < sale.total:
                 return Response(
                    {'error': 'Insufficient payment amount'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Complete sale
        sale.complete_sale()
        
        return Response(
            SaleSerializer(sale).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """Void a sale"""
        sale = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            sale.void_sale(request.user, reason)
            return Response({'status': 'sale voided'})
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@login_required
def pos_screen(request):
    """Main POS screen for creating sales"""
    if not request.user.is_cashier:
        messages.error(request, "You don't have permission to access the POS.")
        return redirect('core:dashboard')
    
    # Get all active products
    products = Product.objects.filter(
        is_active=True
    ).select_related('category').order_by('name')
    
    # Get categories for filtering
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    # Get recent customers
    recent_customers = Customer.objects.filter(
        is_active=True
    ).order_by('-created_at')[:20]
    
    context = {
        'products': products,
        'categories': categories,
        'recent_customers': recent_customers,
    }
    
    return render(request, 'pos/pos_screen.html', context)


@login_required
def sale_detail(request, reference):
    """View sale details and receipt"""
    sale = get_object_or_404(
        Sale.objects.select_related('cashier', 'customer').prefetch_related('items__product', 'payments'),
        reference=reference
    )
    
    context = {
        'sale': sale,
    }
    
    return render(request, 'pos/sale_detail.html', context)


@login_required
def sales_list(request):
    """List all sales"""
    if not request.user.is_cashier:
        messages.error(request, "You don't have permission to view sales.")
        return redirect('core:dashboard')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    
    sales = Sale.objects.select_related('cashier', 'customer').order_by('-created_at')
    
    if status_filter:
        sales = sales.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        sales = sales.filter(
            Q(reference__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(cashier__username__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(sales, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'pos/sales_list.html', context)


@login_required
def print_receipt(request, reference):
    """Print receipt for a sale"""
    sale = get_object_or_404(
        Sale.objects.select_related('cashier', 'customer').prefetch_related('items__product', 'payments'),
        reference=reference
    )
    
    from core.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    
    context = {
        'sale': sale,
        'site_settings': site_settings,
    }
    
    return render(request, 'pos/receipt.html', context)


@login_required
def print_receipt_by_id(request, sale_id):
    """Print receipt for a sale by ID"""
    sale = get_object_or_404(
        Sale.objects.select_related('cashier', 'customer').prefetch_related('items__product', 'payments'),
        id=sale_id
    )
    
    from core.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    
    context = {
        'sale': sale,
        'site_settings': site_settings,
    }
    
    return render(request, 'pos/receipt.html', context)


@require_http_methods(["POST"])
@login_required
def validate_coupon(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        cart_total = float(data.get('cart_total', 0))
        
        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return JsonResponse({'valid': False, 'message': 'Invalid coupon code'})
        
        is_valid, message = coupon.is_valid(cart_total)
        
        if is_valid:
            discount_amount = coupon.calculate_discount(cart_total)
            return JsonResponse({
                'valid': True,
                'code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': float(coupon.discount_value),
                'discount_amount': float(discount_amount),
                'message': 'Coupon applied successfully'
            })
        else:
            return JsonResponse({'valid': False, 'message': message})
            
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)})


@require_http_methods(["GET"])
@login_required
def lookup_customer(request):
    phone = request.GET.get('phone', '').strip()
    
    if not phone:
        return JsonResponse({'found': False})
    
    try:
        customer = Customer.objects.get(phone=phone)
        return JsonResponse({
            'found': True,
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'customer_type': customer.customer_type,
            'discount_percentage': float(customer.discount_percentage),
            'credit_limit': float(customer.credit_limit),
            'current_balance': float(customer.current_balance),
        })
    except Customer.DoesNotExist:
        return JsonResponse({'found': False})


@login_required
def print_receipt(request, reference):
    """Print receipt for a sale"""
    try:
        sale = Sale.objects.select_related('customer', 'cashier').prefetch_related(
            'items__product', 'payments'
        ).get(reference=reference)
        
        context = {
            'sale': sale,
            'site_settings': SiteSettings.objects.first()
        }
        
        return render(request, 'pos/receipt.html', context)
    except Sale.DoesNotExist:
        return HttpResponse("Sale not found", status=404)


@require_http_methods(["GET"])
@login_required
def check_stock(request):
    """Check stock availability for a product"""
    product_id = request.GET.get('product_id')
    quantity = int(request.GET.get('quantity', 1))
    
    if not product_id:
        return JsonResponse({'error': 'Product ID is required'}, status=400)
        
    try:
        product = Product.objects.get(id=product_id)
        
        # Check if enough stock
        if product.stock >= quantity:
            return JsonResponse({
                'available': True,
                'stock': product.stock,
                'price': float(product.sell_price),
                'name': product.name
            })
        else:
            return JsonResponse({
                'available': False,
                'stock': product.stock,
                'message': f'Only {product.stock} units available'
            })
            
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity'}, status=400)


@require_http_methods(["GET"])
@login_required
def search_customers(request):
    """Search customers by name or phone"""
    query = request.GET.get('q', '').strip() or request.GET.get('query', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'customers': []})
    
    # Search by name or phone
    customers = Customer.objects.filter(
        Q(name__icontains=query) | Q(phone__icontains=query),
        is_active=True
    ).order_by('-created_at')[:10]
    
    results = [{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'email': c.email or '',
        'customer_type': c.customer_type,
        'type_display': c.get_customer_type_display(),
        'discount_percentage': float(c.discount_percentage),
    } for c in customers]
    
    return JsonResponse({'customers': results})


@require_http_methods(["POST"])
@login_required
def get_product_price(request):
    """Get product price based on customer type and quantity"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        customer_id = data.get('customer_id')
        quantity = int(data.get('quantity', 1))
        
        if not product_id:
            return JsonResponse({'error': 'Product ID is required'}, status=400)
        
        product = Product.objects.get(id=product_id)
        customer = None
        
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                pass
        
        # Get appropriate price for this customer and quantity
        price, price_type = product.get_price_for_customer(customer, quantity)
        
        return JsonResponse({
            'success': True,
            'product_id': product_id,
            'product_name': product.name,
            'retail_price': float(product.sell_price),
            'price': float(price),
            'price_type': price_type,
            'customer_type': customer.customer_type if customer else 'retail',
            'discount_percentage': float(customer.discount_percentage) if customer else 0,
            'wholesale_price': float(product.wholesale_price) if product.wholesale_price else None,
            'minimum_wholesale_quantity': product.minimum_wholesale_quantity,
            'is_wholesale_eligible': (
                customer and 
                customer.customer_type == 'wholesale' and 
                product.wholesale_price and 
                quantity >= product.minimum_wholesale_quantity
            )
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

