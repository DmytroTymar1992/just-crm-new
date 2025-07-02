from django.db import models
from chats.models import Interaction
from contacts.models import Contact, ContactPhone
from django.utils import timezone


class Call(models.Model):

    interaction = models.ForeignKey(Interaction, on_delete=models.CASCADE, related_name='calls')
    phonet_uuid = models.CharField(max_length=100, unique=True)
    parent_uuid = models.CharField(max_length=100, blank=True, null=True)
    direction = models.PositiveSmallIntegerField(verbose_name="Напрямок дзвінка", help_text="1=internal, 2=outgoing, 4=incoming, etc.")
    leg_id = models.CharField(max_length=100, blank=True, null=True)
    leg_ext = models.CharField(max_length=50, blank=True, null=True)
    leg_name = models.CharField(max_length=100, blank=True, null=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='calls')
    contact_phone = models.ForeignKey(ContactPhone, max_length=20, blank=True, null=True, on_delete=models.CASCADE)
    start_time = models.DateTimeField(blank=True, null=True)
    answer_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    transcription = models.TextField(blank=True, null=True)
    recording_link = models.URLField(blank=True, null=True)
    result = models.CharField(max_length=100, blank=True, null=True, verbose_name="Результат дзвінка")

    def __str__(self):
        return f"{self.direction} call with {self.contact.name} on {self.date}"
