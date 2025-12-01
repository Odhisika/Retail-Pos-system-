
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import User, AuditLog
from catalog.models import Product
from pos.models import Sale
from customers.models import Customer
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UserUpdateForm, UserCreationFormByAdmin, AdminPasswordResetForm


@login_required
def dashboard(request):
    """Main dashboard with key metrics"""
    user = request.user
    
    # Date range - last 7 days
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    previous_start = start_date - timedelta(days=7)
    
    # Weekly revenue
    weekly_sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__gte=start_date,
        created_at__lte=end_date
    ).aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')
    
    # Previous week for comparison
    previous_weekly_sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__gte=previous_start,
        created_at__lt=start_date
    ).aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')
    
    # Calculate percentage change
    if previous_weekly_sales > 0:
        revenue_change = ((weekly_sales - previous_weekly_sales) / previous_weekly_sales) * 100
    else:
        revenue_change = 100 if weekly_sales > 0 else 0
    
    # Total customers
    total_customers = Customer.objects.filter(is_active=True).count()
    
    # Low stock items
    low_stock_items = Product.objects.filter(
        is_active=True,
        track_stock=True
    ).annotate(
        is_low=Q(stock__lte=models.F('low_stock_threshold'))
    ).filter(is_low=True).count()
    
    # Total inventory value
    inventory_value = Product.objects.filter(
        is_active=True
    ).aggregate(
        total=Sum(models.F('cost_price') * models.F('stock'))
    )['total'] or Decimal('0.00')
    
    # Recent sales (last 10)
    recent_sales = Sale.objects.select_related('cashier', 'customer').filter(
        status=Sale.Status.COMPLETED
    ).order_by('-created_at')[:10]
    
    # Sales by day for chart (last 7 days)
    daily_sales = []
    for i in range(6, -1, -1):
        day = end_date - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_total = Sale.objects.filter(
            status=Sale.Status.COMPLETED,
            created_at__gte=day_start,
            created_at__lt=day_end
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        
        daily_sales.append({
            'date': day.strftime('%a'),
            'total': float(day_total)
        })
    
    # Top selling products (last 7 days)
    from pos.models import SaleItem
    top_products = SaleItem.objects.filter(
        sale__status=Sale.Status.COMPLETED,
        sale__created_at__gte=start_date
    ).values(
        'product__name',
        'product__sku'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('line_total')
    ).order_by('-quantity_sold')[:5]
    
    context = {
        'weekly_revenue': weekly_sales,
        'revenue_change': revenue_change,
        'total_customers': total_customers,
        'low_stock_items': low_stock_items,
        'inventory_value': inventory_value,
        'recent_sales': recent_sales,
        'daily_sales': daily_sales,
        'top_products': top_products,
    }
    
    return render(request, 'dashboard.html', context)


def custom_login(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            
            # Log the login
            AuditLog.log(
                user=user,
                action=AuditLog.Action.LOGIN,
                description=f"User {user.username} logged in",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')


@login_required
def custom_logout(request):
    """Custom logout view"""
    # Log the logout
    AuditLog.log(
        user=request.user,
        action=AuditLog.Action.LOGOUT,
        description=f"User {request.user.username} logged out",
        ip_address=get_client_ip(request)
    )
    
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:login')


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def profile(request):
    """User profile view with admin user management"""
    user = request.user
    
    # Handle profile update
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserUpdateForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile has been updated successfully.')
                return redirect('core:profile')
        
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('core:profile')
            else:
                messages.error(request, 'Please correct the errors below.')
    
    # Prepare forms
    profile_form = UserUpdateForm(instance=user)
    password_form = PasswordChangeForm(user)
    
    # Admin-specific data
    all_users = None
    user_creation_form = None
    if user.is_superuser or user.role == 'admin':
        all_users = User.objects.filter(is_superuser=False).exclude(id=user.id).order_by('-date_joined')
        user_creation_form = UserCreationFormByAdmin()
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'page_title': 'User Profile',
        'all_users': all_users,
        'user_creation_form': user_creation_form,
    }
    return render(request, 'core/profile.html', context)


@login_required
def create_user(request):
    """Admin view to create new users"""
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, 'You do not have permission to create users.')
        return redirect('core:profile')
    
    if request.method == 'POST':
        form = UserCreationFormByAdmin(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('core:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('core:profile')


@login_required
def reset_user_password(request, user_id):
    """Admin view to reset user passwords"""
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, 'You do not have permission to reset passwords.')
        return redirect('core:profile')
    
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('core:profile')
    
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            target_user.set_password(form.cleaned_data['new_password1'])
            target_user.save()
            messages.success(request, f'Password for {target_user.username} has been reset successfully!')
            return redirect('core:profile')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    
    return redirect('core:profile')


@login_required
def settings(request):
    """Site settings view for admin and manager"""
    user = request.user
    
    # Check permissions
    if not (user.is_superuser or user.role in ['admin', 'manager']):
        messages.error(request, 'You do not have permission to access settings.')
        return redirect('core:dashboard')
    
    from .models import SiteSettings
    from .forms import SiteSettingsForm
    
    site_settings = SiteSettings.get_settings()
    
    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, instance=site_settings)
        if form.is_valid():
            form.save()
            
            # Log the settings change
            AuditLog.log(
                user=user,
                action=AuditLog.Action.CHANGE_SETTINGS,
                description=f"User {user.username} updated site settings",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Settings updated successfully!')
            return redirect('core:settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SiteSettingsForm(instance=site_settings)
    
    context = {
        'form': form,
        'site_settings': site_settings,
        'page_title': 'Site Settings',
    }
    
    return render(request, 'core/settings.html', context)