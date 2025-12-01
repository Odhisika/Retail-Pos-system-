
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model with role-based access control
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrator')
        MANAGER = 'manager', _('Manager')
        CASHIER = 'cashier', _('Cashier')
        VIEWER = 'viewer', _('Viewer')
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CASHIER,
        help_text=_('User role determines access permissions')
    )
    phone = models.CharField(max_length=20, blank=True)
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    terminal_id = models.CharField(
        max_length=50, 
        blank=True,
        help_text=_('Assigned terminal/register ID')
    )
    is_active_session = models.BooleanField(
        default=False,
        help_text=_('Whether user is currently logged into a POS terminal')
    )
    last_activity = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text=_('User profile picture')
    )
    
    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    def save(self, *args, **kwargs):
        """Override save to auto-assign ADMIN role to superusers"""
        # Automatically set superusers to ADMIN role
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    @property
    def is_manager(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER]
    
    @property
    def is_cashier(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER, self.Role.CASHIER]
    
    @property
    def can_access_reports(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER]
    
    @property
    def can_manage_products(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER]
    
    @property
    def can_manage_users(self):
        return self.role == self.Role.ADMIN


class SiteSettings(models.Model):
    """
    Global site configuration settings
    """
    site_name = models.CharField(max_length=200, default='POS System')
    store_name = models.CharField(max_length=200)
    store_address = models.TextField()
    store_phone = models.CharField(max_length=20)
    store_email = models.EmailField()
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=0.15,
        help_text=_('Default tax rate (e.g., 0.15 for 15%)')
    )
    currency_symbol = models.CharField(max_length=5, default='GH₵')
    currency_code = models.CharField(max_length=3, default='GHS')
    receipt_footer = models.TextField(blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    enable_barcode_scanner = models.BooleanField(default=True)
    enable_customer_loyalty = models.BooleanField(default=True)
    auto_logout_minutes = models.PositiveIntegerField(
        default=5,
        help_text=_('Minutes of inactivity before auto-logout')
    )
    
    class Meta:
        db_table = 'site_settings'
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
    
    def __str__(self):
        return self.site_name
    
    @classmethod
    def get_settings(cls):
        """Get or create singleton settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class AuditLog(models.Model):
    """
    Audit trail for critical system actions
    """
    class Action(models.TextChoices):
        LOGIN = 'login', _('User Login')
        LOGOUT = 'logout', _('User Logout')
        CREATE_SALE = 'create_sale', _('Create Sale')
        VOID_SALE = 'void_sale', _('Void Sale')
        REFUND_SALE = 'refund_sale', _('Refund Sale')
        CREATE_PRODUCT = 'create_product', _('Create Product')
        UPDATE_PRODUCT = 'update_product', _('Update Product')
        DELETE_PRODUCT = 'delete_product', _('Delete Product')
        ADJUST_STOCK = 'adjust_stock', _('Adjust Stock')
        CREATE_USER = 'create_user', _('Create User')
        UPDATE_USER = 'update_user', _('Update User')
        DELETE_USER = 'delete_user', _('Delete User')
        CHANGE_SETTINGS = 'change_settings', _('Change Settings')
        OTHER = 'other', _('Other Action')
    
    user = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=Action.choices)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # JSON field for storing additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Reference to affected object
    content_type = models.CharField(max_length=100, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.get_action_display()} at {self.timestamp}"
    
    @classmethod
    def log(cls, user, action, description, **kwargs):
        """Helper method to create audit log entry"""
        return cls.objects.create(
            user=user,
            action=action,
            description=description,
            **kwargs
        )