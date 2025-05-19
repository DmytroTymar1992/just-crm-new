
# emails/models.py
from django.db import models
from chats.models import Interaction
from contacts.models import Contact
from django.utils import timezone

class EmailMessage(models.Model):
    interaction = models.ForeignKey(Interaction, on_delete=models.CASCADE, related_name='emails')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='email_messages')
    contact_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"Email to {self.contact.name} - {self.subject} on {self.created_at}"


class EmailAttachment(models.Model):
    email = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='email_attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(blank=True, null=True)  # Розмір файлу в байтах
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Attachment {self.file_name} for email {self.email.subject}"

    def save(self, *args, **kwargs):
        # Автоматично зберегти ім’я файлу та розмір, якщо вони не вказані
        if self.file and not self.file_name:
            self.file_name = self.file.name
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
