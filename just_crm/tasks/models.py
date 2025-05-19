from django.db import models
from django.conf import settings
from contacts.models import Contact
from django.utils import timezone


class Task(models.Model):
    # Типи завдань
    TASK_TYPE_CHOICES = [
        ('call', 'Дзвінок'),
        ('email', 'Лист'),
        ('message', 'Повідомлення'),
    ]

    # Атрибути моделі
    created_at = models.DateTimeField("Дата створення", auto_now_add=True)
    task_date = models.DateTimeField("Дата задачі")
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Контакт"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Користувач"
    )
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        verbose_name="Тип задачі"
    )
    target = models.CharField(max_length=255, verbose_name="Ціль")
    description = models.TextField("Опис", blank=True, null=True)
    is_completed = models.BooleanField("Статус", default=False)
    completed_at = models.DateTimeField("Дата виконання", blank=True, null=True)

    def __str__(self):
        return f"Task {self.task_type} for {self.contact} by {self.user} - {self.target}"

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачі"

    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.is_completed:
            self.completed_at = None
        super().save(*args, **kwargs)


class TaskTransfer(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='transfers')
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()

    def __str__(self):
        return f"Transfer of Task {self.task.id} from {self.from_date} to {self.to_date}"

    class Meta:
        verbose_name = "Перенесення задачі"
        verbose_name_plural = "Перенесення задач"