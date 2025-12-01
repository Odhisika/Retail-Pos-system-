
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import transaction
import uuid


class Sale(models.Model):
    """Main sales transaction record"""
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        VOIDED = 'voided', _('Voided')
        REFUNDED = 'refunded', _('Refunded')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PARTIAL = 'partial', _('Partially Paid')
        PAID = 'paid', _('Fully Paid')
    
    # Unique sale reference
    reference = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text=_('Unique sale reference number')
    )
    
    # Relationships
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sales'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchases'
    )
    
    # Amounts
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Total discount amount')
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Payment details
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', _('Cash')),
            ('card', _('Card')),
            ('mobile', _('Mobile Payment')),
            ('credit', _('Credit/Account')),
            ('mixed', _('Mixed Payment')),
        ],
        default='cash'
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Total amount paid so far')
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    notes = models.TextField(blank=True)
    terminal_id = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voided_sales'
    )
    void_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'sales'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['cashier', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Sale {self.reference} - {self.total}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_reference():
        """Generate unique sale reference number"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"SALE-{timestamp}-{unique_id}"
    
    def calculate_totals(self):
        """Calculate and update sale totals from line items"""
        items = self.items.all()
        
        self.subtotal = sum(item.line_total for item in items)
        self.tax = sum(item.tax_amount for item in items)
        self.total = self.subtotal + self.tax - self.discount
        
        self.save(update_fields=['subtotal', 'tax', 'total'])
    
    @transaction.atomic
    def complete_sale(self):
        """Mark sale as completed and adjust inventory"""
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError("Only pending sales can be completed")
        
        # Deduct stock for all items
        for item in self.items.all():
            if item.product.track_stock:
                item.product.adjust_stock(
                    quantity=-item.quantity,
                    reason='sale',
                    performed_by=self.cashier
                )
        
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    @transaction.atomic
    def void_sale(self, user, reason=''):
        """Void a sale and restore inventory"""
        from django.utils import timezone
        
        if self.status == self.Status.VOIDED:
            raise ValueError("Sale is already voided")
        
        # Restore stock for all items
        for item in self.items.all():
            if item.product.track_stock:
                item.product.adjust_stock(
                    quantity=item.quantity,
                    reason='return',
                    performed_by=user
                )
        
        self.status = self.Status.VOIDED
        self.voided_at = timezone.now()
        self.voided_by = user
        self.void_reason = reason
        self.save(update_fields=['status', 'voided_at', 'voided_by', 'void_reason'])


class SaleItem(models.Model):
    """Individual line items in a sale"""
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='sale_items'
    )
    
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Price per unit at time of sale')
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text=_('Tax rate applied to this item')
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    class Meta:
        db_table = 'sale_items'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    @property
    def tax_amount(self):
        """Calculate tax amount for this line item"""
        return (self.unit_price * self.quantity - self.discount) * self.tax_rate
    
    def calculate_line_total(self):
        """Calculate and save line total"""
        subtotal = self.unit_price * self.quantity
        self.line_total = subtotal - self.discount
        self.save(update_fields=['line_total'])
    
    def save(self, *args, **kwargs):
        # Auto-calculate line total if not set
        if not self.line_total:
            self.line_total = (self.unit_price * self.quantity) - self.discount
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment records for sales (supports split payments)"""
    class Method(models.TextChoices):
        CASH = 'cash', _('Cash')
        CARD = 'card', _('Credit/Debit Card')
        MOBILE = 'mobile', _('Mobile Payment')
        CHECK = 'check', _('Check')
        OTHER = 'other', _('Other')
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    method = models.CharField(
        max_length=20,
        choices=Method.choices
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Payment details
    transaction_id = models.CharField(max_length=200, blank=True)
    reference_number = models.CharField(max_length=200, blank=True)
    card_last_four = models.CharField(max_length=4, blank=True)
    
    # Cash-specific fields
    amount_tendered = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Amount given by customer (for cash payments)')
    )
    change_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Change returned to customer')
    )
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_method_display()} - {self.amount}"