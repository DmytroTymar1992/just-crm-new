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
    another_company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name=_('Інша компанія'),
        null=True,
        blank=True,
        related_name='another_contacts'
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

    referral_link = models.URLField(
        max_length=200,
        verbose_name=_('Посилання'),
        blank=True,
        null=True
    )
    has_visited_site = models.BooleanField(
        default=False,
        verbose_name=_('Відвідав сайт')
    )
    is_registered = models.BooleanField(
        default=False,
        verbose_name=_('Зареєстрований')
    )
    is_from_site = models.BooleanField(
        default=False,
        verbose_name=_('З сайту')
    )
    site_user_id = models.CharField(
        max_length=100,
        verbose_name=_('ID на сайті'),
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Чи в роботі')
    )

    class Meta:
        verbose_name = _('Контакт')
        verbose_name_plural = _('Контакти')

    def __str__(self):
        company_name = self.company.name if self.company else "Без компанії"
        last_name = self.last_name or ""
        return f"{self.first_name} {last_name} ({company_name})"

    def save(self, *args, **kwargs):
        # Generate referral link if it's a new contact or link is empty
        if not self.pk or not self.referral_link:
            super().save(*args, **kwargs)  # Save first to get ID
            self.referral_link = f"https://www.just-look.com.ua/?utm={self.pk}"
            super().save(update_fields=['referral_link'])  # Save again with link
        else:
            super().save(*args, **kwargs)


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
        blank=True,
        null=True
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

    has_viber = models.BooleanField(
        default=True,
        verbose_name=_('Є у Viber'),
        help_text=_('false — гарантовано немає Viber; true — або є, або ще не перевірено')
    )
    viber_id = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name=_('Viber ID / number'),
        help_text=_('Поле `from` / `to` з веб-хука; зберігаємо як рядок')
    )
    viber_name = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('Ім’я у Viber')
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