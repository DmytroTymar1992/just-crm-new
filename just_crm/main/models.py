from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', _('Superadmin')),
        ('admin', _('Admin')),
        ('sales', _('Sales')),
        ('marketing', _('Marketing')),
        ('accounting', _('Accounting')),
    )
    STATUS_CHOICES = (
        ('working', _('Working')),
        ('fired', _('Fired')),
        ('on_vacation', _('On Vacation')),
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='sales',
        verbose_name=_('Role'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='working',
        verbose_name=_('Status')
    )

    phonet_extension = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_('Phonet Extension'),
        help_text=_('Internal Phonet extension number (e.g., 001)')
    )

    telegram_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        verbose_name='Telegram ID',
        help_text='Унікальний ID користувача в Telegram (наприклад, 123456789)'
    )

    # -- E-chat канал Viber ----------------------------------------------------
    echat_instance_id = models.CharField(
        max_length=64,
        blank=True, null=True, unique=True,
        verbose_name='E-chat Instance ID',
        help_text='ID каналу (номер Viber), який менеджер підключив у E-chat',
    )
    echat_api_key = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name='E-chat API-Key',
        help_text='Ключ для вихідних запитів (беремо з кабінету E-chat)',
    )

    echat_instance_id_telegram = models.CharField(
        max_length=64,
        blank=True, null=True, unique=True,
        verbose_name='E-chat Instance ID',
        help_text='ID каналу (номер Viber), який менеджер підключив у E-chat',
    )
    echat_api_key_telegram = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name='E-chat API-Key',
        help_text='Ключ для вихідних запитів (беремо з кабінету E-chat)',
    )


    def __str__(self):
        return f"{self.username} ({self.get_role_display()}, {self.get_status_display()})"