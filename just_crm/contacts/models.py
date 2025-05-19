# contacts/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from companies.models import Company

class Contact(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name=_('Компанія'),
        null=True,
        blank=True,
        related_name='contacts'
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name=_('Ім’я')
    )
    last_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Прізвище')
    )
    position = models.CharField(
        max_length=100,
        verbose_name=_('Посада'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата створення')
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name=_('Аватар')
    )

    class Meta:
        verbose_name = _('Контакт')
        verbose_name_plural = _('Контакти')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.company.name})"


class ContactPhone(models.Model):
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        verbose_name=_('Контакт'),
        related_name='phones'
    )
    phone = models.CharField(
        max_length=20,
        verbose_name=_('Телефон'),
        blank=True
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_('Назва'),
        default='Основний'
    )
    telegram_id = models.CharField(
        max_length=50,
        verbose_name=_('Telegram ID'),
        blank=True,
        null=True
    )
    telegram_username = models.CharField(
        max_length=100,
        verbose_name=_('Telegram Username'),
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _('Телефон контакту')
        verbose_name_plural = _('Телефони контактів')

    def __str__(self):
        return f"{self.contact} - {self.phone or self.telegram_username or 'No phone'}"

class ContactEmail(models.Model):
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        verbose_name=_('Контакт'),
        related_name='emails'
    )
    email = models.EmailField(
        verbose_name=_('Email')
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_('Назва'),
        default='Основний'
    )

    class Meta:
        verbose_name = _('Email контакту')
        verbose_name_plural = _('Email контактів')

    def __str__(self):
        return f"{self.contact} - {self.email}"