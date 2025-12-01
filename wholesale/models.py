from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, datetime, date
from customers.models import Customer
from catalog.models import Product
from pos.models import Sale, Payment


class Invoice(models.Model):
    """Invoice model for tracking credit sales and payments"""
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('net_30', 'Net 30'),
        ('net_15', 'Net 15'),
        ('net_7', 'Net 7'),
        ('due_on_receipt', 'Due on Receipt'),
        ('custom', 'Custom'),
    ]
    
    # Invoice identification
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    sale = models.OneToOneField(Sale, null=True, blank=True, on_delete=models.SET_NULL, related_name='invoice')
    
    # Invoice details
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS_CHOICES, default='net_30')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid', db_index=True)
    
    # Additional info
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['customer', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not set
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Calculate due date based on payment terms if not set
        if not self.due_date:
            self.due_date = self.calculate_due_date()
        
        # Update payment status
        self.update_payment_status()
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number in format INV-YYYY-NNNN"""
        from django.db.models import Max
        year = datetime.now().year
        prefix = f"INV-{year}-"
        
        # Get the last invoice number for this year
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=prefix
        ).aggregate(Max('invoice_number'))['invoice_number__max']
        
        if last_invoice:
            last_number = int(last_invoice.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:04d}"
    
    def calculate_due_date(self):
        """Calculate due date based on payment terms"""
        terms_days = {
            'net_30': 30,
            'net_15': 15,
            'net_7': 7,
            'due_on_receipt': 0,
            'custom': 0,
        }
        
        days = terms_days.get(self.payment_terms, 30)
        
        issue_date = self.issue_date
        if isinstance(issue_date, datetime):
            issue_date = issue_date.date()
            
        return issue_date + timedelta(days=days)
    
    def update_payment_status(self):
        """Update payment status based on amount paid"""
        if self.amount_paid <= 0:
            self.payment_status = 'unpaid'
        elif self.amount_paid >= self.total_amount:
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partial'
        
        # Check if overdue
        if self.payment_status != 'paid' and self.due_date < timezone.now().date():
            self.payment_status = 'overdue'
    
    @property
    def balance_due(self):
        """Calculate outstanding balance"""
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.due_date < timezone.now().date() and self.payment_status not in ['paid', 'cancelled']
    
    @property
    def days_until_due(self):
        """Calculate days until due date"""
        delta = self.due_date - timezone.now().date()
        return delta.days


class InvoiceItem(models.Model):
    """Line items for invoices"""
    
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    description = models.CharField(max_length=255)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Calculate total
        subtotal = (self.unit_price * self.quantity) - self.discount
        tax = subtotal * (self.tax_rate / 100)
        self.total = subtotal + tax
        super().save(*args, **kwargs)
    
    @property
    def subtotal(self):
        """Calculate subtotal before tax"""
        return (self.unit_price * self.quantity) - self.discount
    
    @property
    def tax_amount(self):
        """Calculate tax amount"""
        return self.subtotal * (self.tax_rate / 100)


class InvoicePayment(models.Model):
    """Track payments applied to invoices"""
    
    invoice = models.ForeignKey(Invoice, related_name='invoice_payments', on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment for {self.invoice.invoice_number} - {self.amount}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update invoice amount_paid
        self.invoice.amount_paid = self.invoice.invoice_payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.invoice.save()
