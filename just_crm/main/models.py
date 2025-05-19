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

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}, {self.get_status_display()})"