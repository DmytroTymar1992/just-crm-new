from django import forms
from .models import Task
from django.utils import timezone


class TaskForm(forms.ModelForm):
    task_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Дата задачі",
        required=True,
        error_messages={
            'required': 'Будь ласка, вкажіть дату задачі.'
        }
    )

    class Meta:
        model = Task
        fields = ['task_type', 'target', 'task_date', 'description']
        labels = {
            'task_type': 'Тип задачі',
            'target': 'Ціль',
            'description': 'Опис',
        }
        error_messages = {
            'task_type': {
                'required': 'Будь ласка, оберіть тип задачі.'
            },
            'target': {
                'required': 'Будь ласка, вкажіть ціль.'
            },
        }
        widgets = {
            'task_type': forms.Select(choices=Task.TASK_TYPE_CHOICES),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:  # Для редагування
            self.fields['task_date'].widget.attrs['readonly'] = 'readonly'
            self.fields['task_date'].disabled = True
        else:  # Для створення
            self.fields['task_date'].widget.attrs['min'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

    def clean_task_date(self):
        task_date = self.cleaned_data['task_date']
        if not (self.instance and self.instance.pk) and task_date < timezone.now():
            raise forms.ValidationError("Дата задачі не може бути в минулому")
        return task_date


class TaskTransferForm(forms.Form):
    to_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Нова дата",
        required=True,
        input_formats=['%Y-%m-%dT%H:%M'],
        error_messages={
            'required': 'Будь ласка, вкажіть нову дату.'
        }
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Причина перенесення",
        required=True,
        error_messages={
            'required': 'Будь ласка, вкажіть причину перенесення.'
        }
    )

    def clean_to_date(self):
        to_date = self.cleaned_data['to_date']
        if to_date < timezone.now():
            raise forms.ValidationError("Нова дата не може бути в минулому")
        return to_date