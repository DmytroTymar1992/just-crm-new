# companies/forms.py

from django import forms
from contacts.models import Company
from django.core.exceptions import ValidationError

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'work_id', 'rabota_id', 'just_id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'work_id': forms.TextInput(attrs={'class': 'form-control'}),
            'rabota_id': forms.TextInput(attrs={'class': 'form-control'}),
            'just_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_work_id(self):
        work_id = self.cleaned_data.get('work_id')
        if work_id and Company.objects.filter(work_id=work_id).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Цей Work ID уже використовується.')
        return work_id

    def clean_rabota_id(self):
        rabota_id = self.cleaned_data.get('rabota_id')
        if rabota_id and Company.objects.filter(rabota_id=rabota_id).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Цей Rabota ID уже використовується.')
        return rabota_id

    def clean_just_id(self):
        just_id = self.cleaned_data.get('just_id')
        if just_id and Company.objects.filter(just_id=just_id).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Цей Just ID уже використовується.')
        return just_id