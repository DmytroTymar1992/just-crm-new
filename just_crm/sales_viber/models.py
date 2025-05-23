from django.db import models
from main.models import CustomUser
from chats.models import Interaction
from contacts.models import Contact, ContactPhone

class ViberMessage(models.Model):
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
        null=True,
        blank=True,
        related_name='viber_messages',
        verbose_name='Номер телефону'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='viber_messages',
        verbose_name='Користувач'
    )
    text = models.TextField(verbose_name='Текст повідомлення')
    date = models.DateTimeField(verbose_name='Дата', db_index=True)

    class Meta:
        verbose_name = 'Viber повідомлення'
        verbose_name_plural = 'Viber повідомлення'
        ordering = ['-date']

    def __str__(self):
        return f"Viber повідомлення від {self.user.username} до {self.contact} ({self.date})"