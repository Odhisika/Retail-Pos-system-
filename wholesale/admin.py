from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoicePayment


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ('product', 'description', 'quantity', 'unit_price', 'discount', 'tax_rate', 'total')
    readonly_fields = ('total',)


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0
    fields = ('payment', 'amount', 'payment_date', 'notes', 'recorded_by')
    readonly_fields = ('payment_date',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'issue_date', 'due_date', 'total_amount', 'amount_paid', 'balance_due', 'payment_status', 'is_overdue')
    list_filter = ('payment_status', 'payment_terms', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'customer__name', 'customer__phone')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at', 'balance_due')
    inlines = [InvoiceItemInline, InvoicePaymentInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'customer', 'sale')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'payment_terms')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'amount_paid', 'balance_due')
        }),
        ('Status & Details', {
            'fields': ('payment_status', 'notes', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new invoice
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'product', 'quantity', 'unit_price', 'discount', 'tax_rate', 'total')
    list_filter = ('invoice__payment_status',)
    search_fields = ('invoice__invoice_number', 'product__name', 'product__sku')


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'payment', 'amount', 'payment_date', 'recorded_by')
    list_filter = ('payment_date',)
    search_fields = ('invoice__invoice_number', 'notes')
    readonly_fields = ('payment_date',)
