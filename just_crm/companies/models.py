# companies/models.py
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from main.models import CustomUser
from transliterate import translit

class Company(models.Model):
    # Вибір статусів
    STATUS_CHOICES = [
        ('cold_lead', _('Холодний лід')),
        ('warm_lead', _('Теплий лід')),
        ('hot_lead', _('Гарячий лід')),
        ('client', _('Клієнт')),
        ('placed_client', _('Розміщений клієнт')),
        ('paid_client', _('Оплачений клієнт')),
    ]
    name = models.CharField(
        max_length=255,
        verbose_name=_('Назва'),
        unique=False
    )
    work_id = models.CharField(
        max_length=50,
        verbose_name=_('Work ID'),
        blank=True,
        null=True,
        unique=True
    )
    rabota_id = models.CharField(
        max_length=50,
        verbose_name=_('Rabota ID'),
        blank=True,
        null=True,
        unique=True
    )
    just_id = models.CharField(
        max_length=50,
        verbose_name=_('Just ID'),
        blank=True,
        null=True,
        unique=True
    )
    responsible = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        verbose_name=_('Відповідальний'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата створення')
    )
    slug = models.SlugField(
        max_length=255,
        unique=False,
        verbose_name=_('Слаг'),
        allow_unicode=True  # Дозволяє кирилицю
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Чи в роботі')
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='cold_lead',
        verbose_name=_('Статус')
    )

    class Meta:
        verbose_name = _('Компанія')
        verbose_name_plural = _('Компанії')

    def save(self, *args, **kwargs):
        if not self.slug:
            latin_name = translit(self.name, 'uk', reversed=True)
            self.slug = slugify(latin_name, allow_unicode=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def __str__(self):
        return self.name
