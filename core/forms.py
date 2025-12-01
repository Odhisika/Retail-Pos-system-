from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'}),
            'last_name': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'}),
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'}),
            'profile_picture': forms.FileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[#2C3E50] file:text-white hover:file:bg-[#34495E]', 'accept': 'image/*'}),
        }



class UserCreationFormByAdmin(forms.ModelForm):
    """Form for admin to create new users (manager/cashier)"""
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Enter password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Confirm password'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'terminal_id']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Enter username'}),
            'first_name': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Enter last name'}),
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Enter email'}),
            'role': forms.Select(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3'}),
            'terminal_id': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Optional'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class AdminPasswordResetForm(forms.Form):
    """Form for admin to reset user passwords"""
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Enter new password'})
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-[#2C3E50] focus:ring-[#2C3E50] sm:text-sm px-4 py-3', 'placeholder': 'Confirm new password'})
    )
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2


class SiteSettingsForm(forms.ModelForm):
    """Form for editing site settings"""
    class Meta:
        from .models import SiteSettings
        model = SiteSettings
        fields = [
            'site_name', 'store_name', 'store_address', 'store_phone', 'store_email',
            'tax_rate', 'currency_symbol', 'currency_code', 'receipt_footer',
            'low_stock_threshold', 'enable_barcode_scanner', 'enable_customer_loyalty',
            'auto_logout_minutes'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., My POS System'
            }),
            'store_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., ABC Store'
            }),
            'store_address': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'rows': 3,
                'placeholder': 'Enter full store address'
            }),
            'store_phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., +233 XX XXX XXXX'
            }),
            'store_email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., info@store.com'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'step': '0.0001',
                'placeholder': 'e.g., 0.15 for 15%'
            }),
            'currency_symbol': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., GH₵'
            }),
            'currency_code': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., GHS'
            }),
            'receipt_footer': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'rows': 3,
                'placeholder': 'Thank you for your business!'
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., 10'
            }),
            'enable_barcode_scanner': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500'
            }),
            'enable_customer_loyalty': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500'
            }),
            'auto_logout_minutes': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3',
                'placeholder': 'e.g., 5'
            }),
        }
        help_texts = {
            'tax_rate': 'Enter as decimal (e.g., 0.15 for 15% tax)',
            'low_stock_threshold': 'Alert when stock falls below this number',
            'auto_logout_minutes': 'Minutes of inactivity before auto-logout',
        }
