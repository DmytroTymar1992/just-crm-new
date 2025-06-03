from django import forms
from .models import Task
from django.utils import timezone
from datetime import datetime, timedelta, time

def generate_all_times(start=time(9, 0), end=time(18, 0), step_minutes=5):
    """Return list of time objects from start to end with given step."""
    current = datetime.combine(datetime.today(), start)
    end_dt = datetime.combine(datetime.today(), end)
    step = timedelta(minutes=step_minutes)
    times = []
    while current <= end_dt:
        times.append(current.time())
        current += step
    return times

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

        # Choices для всіх слотів часу від 09:00 до 18:00 з кроком 5 хвилин
        self.fields['task_time'].choices = [
            (t.strftime('%H:%M'), t.strftime('%H:%M')) for t in generate_all_times()
        ]

        # Мінімальна допустима дата
        self.fields['task_date'].widget.attrs['min'] = timezone.now().strftime('%Y-%m-%d')

        if self.instance and self.instance.pk:  # Для редагування
            self.fields['task_date'].initial = self.instance.task_date.date()
            self.fields['task_time'].initial = self.instance.task_date.strftime('%H:%M')


    def clean(self):
        cleaned_data = super().clean()
        task_date = cleaned_data.get('task_date')
        task_time = cleaned_data.get('task_time')

        if task_date and task_time:
            try:
                # Об'єднуємо дату і час
                time_obj = datetime.strptime(task_time, '%H:%M').time()
                combined_naive = datetime.combine(task_date, time_obj)
                combined_datetime = timezone.make_aware(combined_naive)
                if combined_datetime < timezone.now():
                    self.add_error('task_date', 'Дата і час задачі не можуть бути в минулому.')

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
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Нова дата",
        required=True,
        error_messages={
            'required': 'Будь ласка, вкажіть нову дату.'
        }
    )
    to_time = forms.ChoiceField(
        label="Новий час",
        required=True,
        error_messages={'required': 'Будь ласка, оберіть час.'}
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Причина перенесення",
        required=True,
        error_messages={
            'required': 'Будь ласка, вкажіть причину перенесення.'
        }
    )

    def __init__(self, *args, user=None, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.task = task

        if user:

            self.fields['to_time'].choices = [
                (t.strftime('%H:%M'), t.strftime('%H:%M')) for t in generate_all_times()
            ]

    def clean(self):
        cleaned_data = super().clean()
        to_date = cleaned_data.get('to_date')
        to_time = cleaned_data.get('to_time')

        if to_date and to_time:
            try:
                time_obj = datetime.strptime(to_time, '%H:%M').time()
                combined_naive = datetime.combine(to_date, time_obj)
                combined_datetime = timezone.make_aware(combined_naive)
                if combined_datetime < timezone.now():
                    self.add_error('to_date', 'Дата і час задачі не можуть бути в минулому.')

                cleaned_data['to_date'] = combined_datetime
            except ValueError:
                self.add_error('to_time', 'Невірний формат часу.')
        return cleaned_data