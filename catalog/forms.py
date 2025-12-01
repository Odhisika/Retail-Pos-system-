
from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku', 'barcode', 'name', 'description', 'category',
            'cost_price', 'sell_price', 'wholesale_price', 'minimum_wholesale_quantity',
            'tax_rate', 'stock', 'low_stock_threshold', 'image', 'unit', 
            'is_active', 'track_stock'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'placeholder': 'Stock Keeping Unit'
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'placeholder': 'e.g., 1234567890123'
            }),
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'placeholder': 'Product name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'rows': 3,
                'placeholder': 'Product description'
            }),
            'category': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'step': '0.01',
                'min': '0'
            }),
            'sell_price': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'step': '0.01',
                'min': '0'
            }),
            'wholesale_price': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'step': '0.01',
                'min': '0'
            }),
            'minimum_wholesale_quantity': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'min': '1'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'step': '0.0001',
                'min': '0',
                'max': '1'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'min': '0'
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'min': '0'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'placeholder': 'e.g., piece, kg, liter'
            }),
            'image': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[#2C3E50] file:text-white hover:file:bg-[#34495E]'
            }),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'parent', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'
            }),
            'description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3',
                'rows': 3
            }),
            'parent': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'
            }),
        }


class ProductImportForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel File',
        widget=forms.FileInput(attrs={
            'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[#2C3E50] file:text-white hover:file:bg-[#34495E]',
            'accept': '.xlsx, .xls'
        }),
        help_text='Upload an Excel file (.xlsx or .xls) containing product data.'
    )