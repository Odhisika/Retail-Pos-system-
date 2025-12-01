from django.core.management.base import BaseCommand
import pandas as pd
from catalog.models import Product, Category

class Command(BaseCommand):
    help = 'Import products from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        df = pd.read_csv(options['file_path'])
        
        for _, row in df.iterrows():
            category, _ = Category.objects.get_or_create(name=row['category'])
            
            Product.objects.update_or_create(
                sku=row['sku'],
                defaults={
                    'name': row['name'],
                    'category': category,
                    'cost_price': row['cost_price'],
                    'sell_price': row['sell_price'],
                    'stock': row.get('stock', 0),
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {len(df)} products'))