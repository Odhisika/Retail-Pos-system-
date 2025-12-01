
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Product, Category
from core.models import SiteSettings

print("--- Site Settings ---")
settings = SiteSettings.get_settings()
print(f"Currency Symbol: {settings.currency_symbol}")
print(f"Currency Code: {settings.currency_code}")

print("\n--- Categories ---")
for cat in Category.objects.all():
    print(f"ID: {cat.id}, Name: {cat.name}, Active: {cat.is_active}")

print("\n--- Products ---")
for p in Product.objects.all():
    print(f"ID: {p.id}, SKU: {p.sku}, Name: {p.name}, Active: {p.is_active}, Category: {p.category.name if p.category else 'None'}, Stock: {p.stock}")
