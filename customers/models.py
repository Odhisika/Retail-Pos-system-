
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Customer(models.Model):
    """Customer profile and information"""
    # Basic information
    customer_id = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text=_('Unique customer identifier')
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Customer categorization
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Comma-separated tags (e.g., VIP, Wholesale, Regular)')
    )
    customer_type = models.CharField(
        max_length=50,
        choices=[
            ('retail', _('Retail')),
            ('wholesale', _('Wholesale')),
            ('vip', _('VIP')),
        ],
        default='retail'
    )
    
    # Loyalty program
    loyalty_points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    loyalty_tier = models.CharField(
        max_length=20,
        choices=[
            ('bronze', _('Bronze')),
            ('silver', _('Silver')),
            ('gold', _('Gold')),
            ('platinum', _('Platinum')),
        ],
        default='bronze'
    )
    
    # Financial
    credit_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Maximum credit allowed for this customer')
    )
    current_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_('Current account balance (for credit accounts)')
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Additional discount percentage for this customer (0-100)')
    )
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    date_of_birth = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_customers'
    )
    
    class Meta:
        db_table = 'customers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['customer_id']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.customer_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = self.generate_customer_id()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_customer_id():
        """Generate unique customer ID"""
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m')
        unique_id = str(uuid.uuid4())[:6].upper()
        return f"CUST-{timestamp}-{unique_id}"
    
    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ', '.join(filter(None, parts))
    
    @property
    def tag_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []
    
    def add_loyalty_points(self, points):
        """Add loyalty points to customer account"""
        self.loyalty_points += points
        self.update_loyalty_tier()
        self.save(update_fields=['loyalty_points', 'loyalty_tier'])
    
    def redeem_loyalty_points(self, points):
        """Redeem loyalty points"""
        if points > self.loyalty_points:
            raise ValueError("Insufficient loyalty points")
        self.loyalty_points -= points
        self.save(update_fields=['loyalty_points'])
    
    def update_loyalty_tier(self):
        """Update loyalty tier based on points"""
        if self.loyalty_points >= 10000:
            self.loyalty_tier = 'platinum'
        elif self.loyalty_points >= 5000:
            self.loyalty_tier = 'gold'
        elif self.loyalty_points >= 2000:
            self.loyalty_tier = 'silver'
        else:
            self.loyalty_tier = 'bronze'
    
    def total_purchases(self):
        """Calculate total purchase amount"""
        from pos.models import Sale
        return Sale.objects.filter(
            customer=self,
            status=Sale.Status.COMPLETED
        ).aggregate(
            total=models.Sum('total')
        )['total'] or 0
    
    def purchase_count(self):
        """Get total number of purchases"""
        from pos.models import Sale
        return Sale.objects.filter(
            customer=self,
            status=Sale.Status.COMPLETED
        ).count()


class CustomerNote(models.Model):
    """Notes and interactions with customers"""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='customer_notes'
    )
    note = models.TextField()
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'customer_notes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.customer.name} at {self.created_at}"
