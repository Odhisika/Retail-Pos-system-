from rest_framework import serializers
from .models import Customer, CustomerNote

class CustomerSerializer(serializers.ModelSerializer):
    full_address = serializers.CharField(read_only=True)
    tag_list = serializers.ListField(read_only=True)
    total_purchases = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    purchase_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['customer_id', 'created_at', 'updated_at']

class CustomerNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = CustomerNote
        fields = '__all__'
        read_only_fields = ['created_at']