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
            self.fields['task_date'].widget.attrs['min'] = timezone.now().strftime('%Y-%m-%d')

            if user:
                date_source = self.data.get('task_date')
                if not date_source and self.instance and self.instance.pk:
                    date_source = self.instance.task_date.date()
                if not date_source:
                    date_source = timezone.now().date()

                if isinstance(date_source, str):
                    try:
                        selected_date = datetime.strptime(date_source, '%Y-%m-%d').date()
                    except ValueError:
                        selected_date = timezone.now().date()
                else:
                    selected_date = date_source

                exclude_id = self.instance.id if self.instance and self.instance.pk else None
                slots = Task.get_available_slots(selected_date, user, exclude_task_id=exclude_id)
                self.fields['task_time'].choices = [
                    (slot.strftime('%H:%M'), slot.strftime('%H:%M')) for slot in slots
                ]

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
                # Перевірка, чи слот вільний
                exclude_id = self.instance.id if self.instance and self.instance.pk else None
                if self.user and Task.objects.filter(
                    user=self.user,
                    task_date=combined_datetime,
                    is_completed=False
                ).exclude(id=exclude_id).exists():
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
            date_str = self.data.get('to_date') or timezone.now().date()
            if isinstance(date_str, str):
                try:
                    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    selected_date = timezone.now().date()
            else:
                selected_date = date_str
            exclude_id = task.id if task else None
            slots = Task.get_available_slots(selected_date, user, exclude_task_id=exclude_id)
            self.fields['to_time'].choices = [
                (slot.strftime('%H:%M'), slot.strftime('%H:%M')) for slot in slots
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
                exclude_id = self.task.id if self.task else None
                if self.user and Task.objects.filter(
                    user=self.user,
                    task_date=combined_datetime,
                    is_completed=False
                ).exclude(id=exclude_id).exists():
                    self.add_error('to_time', 'Цей часовий слот уже зайнятий.')
                cleaned_data['to_date'] = combined_datetime
            except ValueError:
                self.add_error('to_time', 'Невірний формат часу.')
        return cleaned_data