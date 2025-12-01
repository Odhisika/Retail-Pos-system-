from rest_framework import serializers
from .models import Sale, SaleItem, Payment
from catalog.serializers import ProductSerializer

class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = SaleItem
        fields = '__all__'
        read_only_fields = ['line_total']

class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['created_at', 'processed_at']

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source='cashier.get_full_name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ['reference', 'created_at', 'completed_at', 'voided_at']

class CreateSaleSerializer(serializers.Serializer):
    """Serializer for creating a complete sale with items and payments"""
    customer_name = serializers.CharField(required=True)
    customer_phone = serializers.CharField(required=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    items = serializers.ListField(child=serializers.DictField())
    payments = serializers.ListField(child=serializers.DictField())
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)