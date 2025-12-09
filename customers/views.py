from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import IsCashier
from .models import Customer, CustomerNote
from .serializers import CustomerSerializer, CustomerNoteSerializer

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator

from .models import Customer, CustomerNote
from .forms import CustomerForm
from pos.models import Sale
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsCashier]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer_type', 'loyalty_tier', 'is_active']
    search_fields = ['customer_id', 'name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']

class CustomerNoteViewSet(viewsets.ModelViewSet):
    queryset = CustomerNote.objects.select_related('customer', 'created_by').all()
    serializer_class = CustomerNoteSerializer
    permission_classes = [IsCashier]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['customer']




@login_required
def customer_list(request):
    """List all customers"""
    search_query = request.GET.get('search', '')
    customer_type = request.GET.get('type', '')
    
    customers = Customer.objects.all()
    
    if search_query:
        customers = customers.filter(
            Q(customer_id__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
    
    # Annotate with purchase stats
    customers = customers.annotate(
        total_spent=Sum('purchases__total', filter=Q(purchases__status=Sale.Status.COMPLETED)),
        purchase_count=Count('purchases', filter=Q(purchases__status=Sale.Status.COMPLETED))
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'customer_type': customer_type,
    }
    
    return render(request, 'customers/customer_list.html', context)


@login_required
def customer_detail(request, pk):
    """View customer details"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Get purchase history
    purchases = Sale.objects.filter(
        customer=customer,
        status=Sale.Status.COMPLETED
    ).order_by('-created_at')[:20]
    
    # Get notes
    notes = customer.customer_notes.select_related('created_by').order_by('-created_at')
    
    # Calculate stats
    stats = Sale.objects.filter(
        customer=customer,
        status=Sale.Status.COMPLETED
    ).aggregate(
        total_spent=Sum('total'),
        total_purchases=Count('id')
    )
    
    if stats['total_purchases'] and stats['total_purchases'] > 0:
        stats['average_purchase'] = stats['total_spent'] / stats['total_purchases']
    else:
        stats['average_purchase'] = 0
    
    context = {
        'customer': customer,
        'purchases': purchases,
        'notes': notes,
        'stats': stats,
    }
    
    return render(request, 'customers/customer_detail.html', context)


@login_required
def customer_create(request):
    """Create new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            
            messages.success(request, f'Customer "{customer.name}" created successfully.')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'customers/customer_form.html', context)


@login_required
def customer_update(request, pk):
    """Update customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Customer "{customer.name}" updated successfully.')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
        'action': 'Update',
    }
    
    return render(request, 'customers/customer_form.html', context)


@login_required
def customer_delete(request, pk):
    """Delete customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        customer_name = customer.name
        customer.delete()
        messages.success(request, f'Customer "{customer_name}" deleted successfully.')
        return redirect('customers:customer_list')
    
    # If GET request, show confirmation
    context = {
        'customer': customer,
    }
    return render(request, 'customers/customer_confirm_delete.html', context)
@require_http_methods(["POST"])
@login_required
def register_customer_api(request):
    """API endpoint to register a new customer from POS"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip() if data.get('email') else None
        
        # Validation
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)
        
        if not phone:
            return JsonResponse({'success': False, 'error': 'Phone number is required'}, status=400)
        
        # Validate Ghana phone number (10 digits, starts with 0)
        if len(phone) != 10 or not phone.startswith('0') or not phone.isdigit():
            return JsonResponse({
                'success': False, 
                'error': 'Invalid phone number. Must be 10 digits starting with 0'
            }, status=400)
        
        # Check if customer with this phone already exists
        if Customer.objects.filter(phone=phone).exists():
            return JsonResponse({
                'success': False, 
                'error': 'A customer with this phone number already exists'
            }, status=400)
        
        # Validate email if provided
        if email:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'success': False, 'error': 'Invalid email address'}, status=400)
        
        # Create customer
        customer = Customer.objects.create(
            name=name,
            phone=phone,
            email=email,
            customer_type='retail',  # Default to retail
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'customer_type': customer.customer_type,
                'discount_percentage': float(customer.discount_percentage or 0),
                'type_display': customer.get_customer_type_display()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)