from django.db import models
from django.utils.translation import gettext_lazy as _
from companies.models import Company
from contacts.models import Contact

class Vacancy(models.Model):
    STATUS_CHOICES = [
        ('standard', _('Стандарт')),
        ('standard_plus', _('Стандарт+')),
        ('hot', _('Гаряча')),
    ]

    title = models.CharField(
        max_length=255,
        verbose_name=_('Назва'),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name=_('Компанія'),
        related_name='vacancies'
    )
    work_id = models.CharField(
        max_length=50,
        verbose_name=_('Work ID'),
        blank=True,
        null=True
    )
    rabota_id = models.CharField(
        max_length=50,
        verbose_name=_('Rabota ID'),
        blank=True,
        null=True
    )
    just_id = models.CharField(
        max_length=50,
        verbose_name=_('Just ID'),
        blank=True,
        null=True
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        verbose_name=_('Контакт'),
        null=True,
        blank=True,
        related_name='vacancies'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата створення')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Чи активна')
    )
    is_new = models.BooleanField(
        default=True,
        verbose_name=_('Чи нова')
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_('Місто'),
        blank=True,
        null=True
    )
    link = models.URLField(
        max_length=200,
        verbose_name=_('Посилання'),
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='standard',
        verbose_name=_('Статус')
    )

    class Meta:
        verbose_name = _('Вакансія')
        verbose_name_plural = _('Вакансії')

    def __str__(self):
        return f"{self.title} ({self.company.name})"
