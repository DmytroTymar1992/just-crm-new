from django.db import models
from django.utils import timezone
from chats.models import Chat
from contacts.models import Contact
from main.models import CustomUser

class AiSuggestion(models.Model):
    class ActionType(models.TextChoices):
        CALL    = "Дзвінок", "Дзвінок"
        EMAIL   = "лист",    "Лист"
        MESSAGE = "повідомлення", "Повідомлення"

    chat   = models.OneToOneField(             # 1 запис на чат
        Chat,
        on_delete=models.CASCADE,
        related_name="ai_suggestion",
        primary_key=True,
        verbose_name="Чат"
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE,
        related_name="ai_suggestions", verbose_name="Контакт"
    )
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name="ai_suggestions", verbose_name="Користувач"
    )

    type  = models.CharField(
        max_length=15, choices=ActionType.choices,
        verbose_name="Тип дії"
    )
    goal  = models.CharField(max_length=255, verbose_name="Ціль")
    short_description = models.TextField(verbose_name="Короткий опис")

    updated_at = models.DateTimeField(default=timezone.now, verbose_name="Оновлено")

    def __str__(self):
        return f"{self.chat} → {self.type}: {self.goal[:30]}"

