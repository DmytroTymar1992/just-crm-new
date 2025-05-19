from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from contacts.models import Contact, ContactPhone, ContactEmail
from contacts.utils import normalize_phone_number


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['company', 'first_name', 'last_name', 'position']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),

        }

class ContactPhoneForm(forms.ModelForm):
    class Meta:
        model = ContactPhone
        fields = ['name', 'phone', 'telegram_id', 'telegram_username']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_id': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            normalized_phone = normalize_phone_number(phone)
            if normalized_phone is None:
                raise ValidationError('Некоректний формат номера телефону.')

            # Перевіряємо, чи існує нормалізований номер у базі
            existing_phone = ContactPhone.objects.filter(phone=normalized_phone).exclude(
                contact=self.instance.contact if self.instance.pk else None
            ).first()
            if existing_phone:
                raise ValidationError(f'Цей номер телефону вже використовується для контакта {existing_phone.contact}.')

            return normalized_phone
        return phone

class ContactEmailForm(forms.ModelForm):
    class Meta:
        model = ContactEmail
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

ContactPhoneFormSet = inlineformset_factory(
    Contact,
    ContactPhone,
    form=ContactPhoneForm,
    extra=1,
    can_delete=True
)

ContactEmailFormSet = inlineformset_factory(
    Contact,
    ContactEmail,
    form=ContactEmailForm,
    extra=1,
    can_delete=True
)