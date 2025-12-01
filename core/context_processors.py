from .models import SiteSettings

def site_settings(request):
    """Add site settings to template context"""
    return {
        'site_settings': SiteSettings.get_settings()
    }

def notifications(request):
    """Add recent system activities to template context"""
    if not request.user.is_authenticated:
        return {}
        
    from pos.models import Sale
    from customers.models import Customer
    from catalog.models import Product
    
    recent_sales = Sale.objects.order_by('-created_at')[:5]
    recent_customers = Customer.objects.order_by('-created_at')[:5]
    recent_products = Product.objects.order_by('-created_at')[:5]
    
    # Combine and sort by created_at (simplified for now, just passing separate lists)
    # or we can create a unified list of "activities"
    
    return {
        'recent_sales': recent_sales,
        'recent_customers': recent_customers,
        'recent_products': recent_products,
    }