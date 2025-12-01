from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth.views import LoginView, LogoutView
from rest_framework.routers import DefaultRouter
from catalog.views import CategoryViewSet, ProductViewSet, InventoryAdjustmentViewSet
from pos.views import SaleViewSet
from customers.views import CustomerViewSet, CustomerNoteViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet)
router.register('inventory-adjustments', InventoryAdjustmentViewSet)
router.register('sales', SaleViewSet)
router.register('customers', CustomerViewSet)
router.register('customer-notes', CustomerNoteViewSet)

urlpatterns = [
    # Root redirect to login
    path('', RedirectView.as_view(url='login/', permanent=False)),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Auth URLs
    path('login/', LoginView.as_view(template_name='login.html', next_page='core:dashboard'), name='login'),
    path('logout/', LogoutView.as_view(next_page='core:login'), name='logout'),
    
    # API
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    
    # App URLs
    path('', include('core.urls')),
    path('pos/', include('pos.urls', namespace='pos')),
    path('catalog/', include('catalog.urls', namespace='catalog')),
    path('customers/', include('customers.urls', namespace='customers')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('wholesale/', include('wholesale.urls', namespace='wholesale')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)