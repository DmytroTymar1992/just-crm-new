# sales_viber/services.py
from django.utils import timezone
from contacts.utils import normalize_phone_number
from contacts.models import Contact, ContactPhone
from chats.models import Chat, Interaction
from .models import ViberMessage
from .tasks import send_viber_message
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def get_or_create_chat(user, contact):
    from chats.models import Chat
    chat, _ = Chat.objects.get_or_create(
        user=user, contact=contact,
        defaults={"title": f"Viber: {contact.first_name}"}
    )
    return chat


def send_text_in_chat(user, chat: Chat, text: str) -> ViberMessage:
    """
    Використовує існуючий Chat ⇒ контакт ⇒ телефон,
    створює Interaction + ViberMessage(pending) + Celery-таску.
    """
    phone = chat.contact.phones.first()          # 1-й номер контакту
    if not phone:
        raise ValueError("У контакта немає телефону")

    inter = Interaction.objects.create(
        user=user, chat=chat, contact=chat.contact,
        contact_phone=phone, date=timezone.now(),
        interaction_type='viber', sender='user', is_read=True, user_last_name=user.last_name,
        user_first_name=user.first_name
    )

    msg = ViberMessage.objects.create(
        interaction=inter, contact=chat.contact,
        contact_phone=phone, user=user,
        text=text, date=timezone.now(),
        delivery_status='pending', raw_event={}
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{msg.user.id}_chats',
        {'type': 'update_chats'}
    )
    async_to_sync(channel_layer.group_send)(
        f'chat_{msg.interaction.chat.id}',
        {
            'type': 'update_interaction',
            'interaction_id': inter.id,
        }
    )

    send_viber_message.delay(msg.id)
    return msg