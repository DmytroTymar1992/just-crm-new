from django.db import models
from django.conf import settings
from chats.models import Interaction, Chat
from contacts.models import Contact, ContactPhone

class TelegramMessage(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Текст'
        MIXED = 'mixed', 'Текст + Файли'

    interaction = models.ForeignKey(
        Interaction,
        on_delete=models.CASCADE,
        related_name='telegram_messages',
        verbose_name='Взаємодія'
    )
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='telegram_messages',
        verbose_name='Чат'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='telegram_messages',
        verbose_name='Контакт'
    )
    contact_phone = models.ForeignKey(
        ContactPhone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='telegram_messages',
        verbose_name='Номер телефону'
    )
    telegram_chat_id = models.CharField(
        max_length=100,
        verbose_name='Telegram Chat ID',
        help_text='ID чату в Telegram (наприклад, -1001234567890)'
    )
    message_id = models.CharField(
        max_length=100,
        verbose_name='Message ID',
        help_text='Унікальний ID повідомлення в Telegram'
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name='Тип повідомлення'
    )
    text = models.TextField(
        verbose_name='Текст повідомлення',
        blank=True
    )
    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата',
        db_index=True
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )

    class Meta:
        verbose_name = 'Повідомлення Telegram'
        verbose_name_plural = 'Повідомлення Telegram'
        ordering = ['-date']

    def __str__(self):
        sender = self.interaction.user.username if self.interaction.sender == 'user' else f"{self.contact.first_name} {self.contact.last_name or ''}"
        return f"Повідомлення від {sender} в {self.telegram_chat_id} ({self.date})"


class TelegramMessageMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Зображення'
        DOCUMENT = 'document', 'Документ'
        VOICE = 'voice', 'Голосове'
        VIDEO = 'video', 'Відео'

    telegram_message = models.ForeignKey(
        TelegramMessage,
        on_delete=models.CASCADE,
        related_name='media_files',
        verbose_name='Повідомлення Telegram'
    )
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        verbose_name='Тип медіа'
    )
    file_url = models.URLField(
        max_length=500,
        verbose_name='URL файлу'
    )
    file_id = models.CharField(
        max_length=100,
        verbose_name='File ID',
        help_text='Унікальний ID файлу в Telegram'
    )

    class Meta:
        verbose_name = 'Медіафайл Telegram'
        verbose_name_plural = 'Медіафайли Telegram'

    def __str__(self):
        return f"{self.media_type} для повідомлення {self.telegram_message.message_id}"