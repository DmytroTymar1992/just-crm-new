from django import forms
from .models import Task
from django.utils import timezone
from datetime import datetime


class TaskForm(forms.ModelForm):
    task_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Дата задачі",
        required=True,
        error_messages={'required': 'Будь ласка, вкажіть дату задачі.'}
    )
    task_time = forms.ChoiceField(
        label="Час задачі",
        required=True,
        error_messages={'required': 'Будь ласка, оберіть час задачі.'}
    )

    class Meta:
        model = Task
        fields = ['task_type', 'target', 'task_date', 'task_time', 'description']
        labels = {
            'task_type': 'Тип задачі',
            'target': 'Ціль',
            'description': 'Опис',
        }
        error_messages = {
            'task_type': {'required': 'Будь ласка, оберіть тип задачі.'},
            'target': {'required': 'Будь ласка, вкажіть ціль.'},
        }
        widgets = {
            'task_type': forms.Select(choices=Task.TASK_TYPE_CHOICES),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if self.instance and self.instance.pk:  # Для редагування
            self.fields['task_date'].initial = self.instance.task_date.date()
            self.fields['task_time'].initial = self.instance.task_date.strftime('%H:%M')
            self.fields['task_date'].widget.attrs['readonly'] = 'readonly'
            self.fields['task_time'].widget.attrs['readonly'] = 'readonly'
            self.fields['task_date'].disabled = True
            self.fields['task_time'].disabled = True
        else:  # Для створення
            self.fields['task_date'].widget.attrs['min'] = timezone.now().strftime('%Y-%m-%d')
            # Ініціалізація слотів для поточної дати
            if user:
                today = timezone.now().date()
                slots = Task.get_available_slots(today, user)
                self.fields['task_time'].choices = [(slot.strftime('%H:%M'), slot.strftime('%H:%M')) for slot in slots]

    def clean(self):
        cleaned_data = super().clean()
        task_date = cleaned_data.get('task_date')
        task_time = cleaned_data.get('task_time')

        if task_date and task_time and not (self.instance and self.instance.pk):
            try:
                # Об'єднуємо дату і час
                time_obj = datetime.strptime(task_time, '%H:%M').time()
                combined_datetime = datetime.combine(task_date, time_obj)
                if combined_datetime < timezone.now():
                    self.add_error('task_date', 'Дата і час задачі не можуть бути в минулому.')
                # Перевірка, чи слот вільний
                if self.user and Task.objects.filter(
                    user=self.user,
                    task_date=combined_datetime,
                    is_completed=False
                ).exists():
                    self.add_error('task_time', 'Цей часовий слот уже зайнятий.')
                cleaned_data['task_date'] = combined_datetime
            except ValueError:
                self.add_error('task_time', 'Невірний формат часу.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # task_date уже містить об'єднану дату і час з clean()
        if commit:
            instance.save()
        return instance


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