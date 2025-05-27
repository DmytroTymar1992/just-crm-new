from django.db import models
from django.conf import settings
from main.models import CustomUser
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

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='telegram_messages',
        verbose_name='Користувач'
    )

    media_url = models.URLField(
        null=True, blank=True,
        verbose_name='URL медіа-файлу'
    )
    media_type = models.CharField(
        max_length=20, null=True, blank=True,
        choices=[
            ('image', 'Image'),
            ('video', 'Video'),
            ('file', 'File'),
            ('sticker', 'Sticker')
        ],
        verbose_name='Тип медіа'
    )

    echat_message_id = models.CharField(
        max_length=100,
        verbose_name='Message ID',
        help_text='Унікальний ID повідомлення в Telegram',
        blank=True,
        null=True
    )
    delivery_status = models.CharField(
        max_length=12, db_index=True,
        choices=[
            ('pending', 'Очікує'),
            ('sent', 'Надіслано'),
            ('delivered', 'Доставлено'),
            ('read', 'Прочитано'),
            ('failed', 'Помилка')
        ],
        default='pending',
        verbose_name='Статус доставки'
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
    error_code = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name='Код/опис помилки'
    )

    raw_event = models.JSONField(
        verbose_name='Сирий payload веб-хука',
        help_text='Зберігайте тут повний JSON, тоді нові поля веб-хука не зламають парсер.'
    )


    class Meta:
        verbose_name = 'Повідомлення Telegram'
        verbose_name_plural = 'Повідомлення Telegram'
        ordering = ['-date']

    def __str__(self):
        sender = self.interaction.user.username if self.interaction.sender == 'user' else f"{self.contact.first_name} {self.contact.last_name or ''}"
        return f"Повідомлення від {sender} ({self.date})"


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