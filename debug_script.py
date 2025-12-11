from pos.serializers import CreateSaleSerializer
from catalog.models import Product
from customers.models import Customer
from django.contrib.auth import get_user_model

def run():
    print("Starting debug...")
    try:
        product = Product.objects.first()
        customer = Customer.objects.first()
        if not customer:
            customer = Customer.objects.create(name="Test", phone="123")
        
        data = {
            'customer_name': customer.name,
            'customer_phone': customer.phone,
            'customer_email': '',
            'items': [{'product_id': product.id, 'quantity': 1, 'discount': 0}],
            'payments': [{'method': 'cash', 'amount': str(product.price), 'amount_tendered': str(product.price), 'change_amount': 0}],
            'discount': 0,
            'notes': 'Debug'
        }
        print(f"Data: {data}")
        
        serializer = CreateSaleSerializer(data=data)
        if serializer.is_valid():
            print("Serializer VALID")
        else:
            print(f"Serializer ERRORS: {serializer.errors}")
            
    except Exception as e:
        print(f"Error: {e}")

run()
