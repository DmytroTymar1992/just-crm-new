from django.db import models
from main.models import CustomUser
from contacts.models import Contact, ContactPhone, ContactEmail
from django.utils import timezone

class Chat(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='chats')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='chats')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Chat between {self.user.username} and {self.contact.name}"


class Interaction(models.Model):
    class InteractionType(models.TextChoices):
        TELEGRAM = 'telegram', 'Telegram'
        EMAIL = 'email', 'Email'
        CALL = 'call', 'Call'
        VIBER = 'viber', 'Viber'
        SYSTEM = 'system', 'System'

    class SenderType(models.TextChoices):
        USER = 'user', 'User'
        CONTACT = 'contact', 'Contact'
        SYSTEM = 'system', 'System'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='interactions', verbose_name='Користувач')
    chat = models.ForeignKey('Chat', on_delete=models.CASCADE, related_name='interactions', null=True, blank=True, verbose_name='Чат')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='interactions', verbose_name='Контакт')
    contact_phone = models.ForeignKey(ContactPhone, max_length=20, blank=True, null=True, verbose_name='Телефон контакта', on_delete=models.CASCADE)
    contact_email = models.ForeignKey(ContactEmail, blank=True, null=True, verbose_name='Емейл контакта', on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now, verbose_name='Дата')
    interaction_type = models.CharField(max_length=20, choices=InteractionType.choices, verbose_name='Тип')
    sender = models.CharField(max_length=20, choices=SenderType.choices, verbose_name='Відправник')
    description = models.TextField(blank=True, verbose_name='Опис')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    user_first_name = models.CharField(max_length=50, null=True, blank=True)
    user_last_name = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.interaction_type} interaction with {self.contact.name} by {self.sender} on {self.date}"