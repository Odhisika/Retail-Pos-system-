
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Category(models.Model):
    """Product categories for organization"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def full_path(self):
        """Return full category path (e.g., Electronics > Computers > Laptops)"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class Product(models.Model):
    """Product catalog items"""
    sku = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Stock Keeping Unit - unique product identifier')
    )
    barcode = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Barcode for scanner input')
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    
    # Pricing
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Cost/wholesale price')
    )
    sell_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Retail selling price')
    )
    wholesale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_('Wholesale price for wholesale customers')
    )
    minimum_wholesale_quantity = models.PositiveIntegerField(
        default=1,
        help_text=_('Minimum quantity for wholesale pricing')
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.15,
        help_text=_('Tax rate for this product (e.g., 0.15 for 15%)')
    )
    
    # Inventory
    stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Current stock quantity')
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text=_('Alert when stock falls below this level')
    )
    
    # Product details
    image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True
    )
    unit = models.CharField(
        max_length=20,
        default='piece',
        help_text=_('Unit of measurement (piece, kg, liter, etc.)')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether product is available for sale')
    )
    track_stock = models.BooleanField(
        default=True,
        help_text=_('Whether to track inventory for this product')
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_products'
    )
    
    class Meta:
        db_table = 'products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.sku} - {self.name}"
    
    @property
    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.track_stock and self.stock <= self.low_stock_threshold
    
    @property
    def inventory_value(self):
        """Calculate total inventory value (cost_price * stock)"""
        return self.cost_price * self.stock
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return ((self.sell_price - self.cost_price) / self.cost_price) * 100
        return 0
    
    def can_sell(self, quantity=1):
        """Check if product can be sold in given quantity"""
        if not self.is_active:
            return False
        if self.track_stock and self.stock < quantity:
            return False
        return True
    
    def adjust_stock(self, quantity, reason='', performed_by=None):
        """Adjust stock level and create inventory adjustment record"""
        old_stock = self.stock
        self.stock += quantity
        self.save(update_fields=['stock'])
        
        # Create inventory adjustment record
        InventoryAdjustment.objects.create(
            product=self,
            quantity_change=quantity,
            old_stock=old_stock,
            new_stock=self.stock,
            reason=reason,
            performed_by=performed_by
        )

    def get_price_for_customer(self, customer=None, quantity=1):
        """
        Get appropriate price for a customer based on their type and quantity.
        Returns tuple: (price, price_type)
        """
        # Default to retail price
        price = self.sell_price
        price_type = 'retail'
        
        if customer and customer.customer_type == 'wholesale':
            # Check if wholesale price is set
            if self.wholesale_price and self.wholesale_price > 0:
                # Check if quantity meets minimum
                if quantity >= self.minimum_wholesale_quantity:
                    price = self.wholesale_price
                    price_type = 'wholesale'
        
        # Apply customer-specific discount if applicable
        if customer and customer.discount_percentage > 0:
            discount_amount = price * (customer.discount_percentage / 100)
            price = price - discount_amount
            price_type = f'{price_type} +{customer.discount_percentage}% discount'
        
        return price, price_type


class InventoryAdjustment(models.Model):
    """Track all inventory adjustments for audit trail"""
    class Reason(models.TextChoices):
        SALE = 'sale', _('Sale')
        RETURN = 'return', _('Customer Return')
        DAMAGE = 'damage', _('Damaged/Lost')
        RESTOCK = 'restock', _('Restocking')
        CORRECTION = 'correction', _('Stock Correction')
        TRANSFER = 'transfer', _('Transfer')
        OTHER = 'other', _('Other')
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='adjustments'
    )
    quantity_change = models.IntegerField(
        help_text=_('Positive for additions, negative for subtractions')
    )
    old_stock = models.IntegerField()
    new_stock = models.IntegerField()
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        default=Reason.OTHER
    )
    notes = models.TextField(blank=True)
    
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_adjustments'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_adjustments'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['product', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.product.sku} - {self.quantity_change:+d} at {self.timestamp}"


class Supplier(models.Model):
    """Supplier/vendor information (optional for future use)"""
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'suppliers'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    times_used = models.IntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_coupons')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'coupons'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"
    
    def is_valid(self, cart_total=None):
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False, "Coupon is not active"
        if now < self.valid_from:
            return False, "Coupon is not yet valid"
        if now > self.valid_to:
            return False, "Coupon has expired"
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False, "Coupon usage limit reached"
        if cart_total is not None and cart_total < self.min_purchase:
            return False, f"Minimum purchase required"
        
        return True, "Valid"
    
    def calculate_discount(self, cart_total):
        if self.discount_type == 'percentage':
            discount = cart_total * (self.discount_value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value
        return min(discount, cart_total)
