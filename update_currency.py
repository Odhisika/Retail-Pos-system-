
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import SiteSettings

# Update the site settings
settings = SiteSettings.get_settings()
settings.currency_symbol = 'GH₵'
settings.currency_code = 'GHS'
settings.save()

print("✓ Currency updated successfully!")
print(f"  Currency Symbol: {settings.currency_symbol}")
print(f"  Currency Code: {settings.currency_code}")
