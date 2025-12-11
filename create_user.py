from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='debug_cashier').exists():
    User.objects.create_user('debug_cashier', 'debug@example.com', 'password123', is_staff=True, is_cashier=True)
    print("User created")
else:
    print("User already exists")
