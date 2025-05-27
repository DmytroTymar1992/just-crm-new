from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ViberMessage
from contacts.models import ContactPhone


@receiver(post_save, sender=ViberMessage)
def update_phone_meta_from_viber(sender, instance: ViberMessage, created, **kwargs):
    """
    Після кожного збереження ViberMessage:
    1. встановлюємо has_viber=True
    2. зберігаємо viber_id та viber_name, якщо вони прийшли
    """
    if not created or not instance.contact_phone:
        return

    phone = instance.contact_phone
    updated = False

    if not phone.has_viber:
        phone.has_viber = True
        updated = True

    # 'from' / 'to' у raw_event містить номер / ID
    viber_id = instance.raw_event.get('from') or instance.raw_event.get('to')
    if viber_id and phone.viber_id != viber_id:
        phone.viber_id = viber_id
        updated = True

    viber_name = instance.raw_event.get('sender_name')
    if viber_name and phone.viber_name != viber_name:
        phone.viber_name = viber_name
        updated = True

    if updated:
        phone.save(update_fields=['has_viber', 'viber_id', 'viber_name'])
