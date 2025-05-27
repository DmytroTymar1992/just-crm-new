from django.db import models
from main.models import CustomUser
from chats.models import Interaction
from contacts.models import Contact, ContactPhone


class ViberMessage(models.Model):
    """Зберігає ВСІ івенти Viber — текст, медіа, статус доставки та помилки."""
    interaction = models.ForeignKey(
        Interaction,
        on_delete=models.CASCADE,
        related_name='viber_messages',
        verbose_name='Взаємодія'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='viber_messages',
        verbose_name='Контакт'
    )
    contact_phone = models.ForeignKey(
        ContactPhone,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='viber_messages',
        verbose_name='Номер телефону'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='viber_messages',
        verbose_name='Користувач'
    )

    # ===== вміст повідомлення =================================================
    text = models.TextField(verbose_name='Текст повідомлення', blank=True)
    media_url = models.URLField(
        null=True, blank=True,
        verbose_name='URL медіа-файлу'
    )
    media_type = models.CharField(
        max_length=20, null=True, blank=True,
        choices=[
            ('image', 'Image'),
            ('video', 'Video'),
            ('file',  'File'),
            ('sticker', 'Sticker')
        ],
        verbose_name='Тип медіа'
    )

    # ===== службові поля ======================================================
    echat_message_id = models.CharField(
        max_length=64, unique=True,
        verbose_name='ID у E-chat',
        null=True,
        blank=True
    )
    delivery_status = models.CharField(
        max_length=12, db_index=True,
        choices=[
            ('pending',   'Очікує'),
            ('sent',      'Надіслано'),
            ('delivered', 'Доставлено'),
            ('read',      'Прочитано'),
            ('failed',    'Помилка')
        ],
        default='pending',
        verbose_name='Статус доставки'
    )
    error_code = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name='Код/опис помилки'
    )

    raw_event = models.JSONField(
        verbose_name='Сирий payload веб-хука',
        help_text='Зберігайте тут повний JSON, тоді нові поля веб-хука не зламають парсер.'
    )

    date = models.DateTimeField(verbose_name='Дата події', db_index=True)

    class Meta:
        verbose_name = 'Viber повідомлення'
        verbose_name_plural = 'Viber повідомлення'
        ordering = ['-date']

    def __str__(self):
        return f"[{self.delivery_status}] {self.contact} ↔ {self.user.username} ({self.date:%Y-%m-%d %H:%M})"
