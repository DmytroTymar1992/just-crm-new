# sales_viber/views.py
import json, logging
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from contacts.utils import normalize_phone_number
from contacts.models import Contact, ContactPhone
from main.models import CustomUser
from chats.models import Interaction
from .models import ViberMessage
from chats.models import Chat


logger = logging.getLogger(__name__)

def get_or_create_chat(user: CustomUser, contact: Contact) -> Chat:
    """
    Повертає існуючий chat user+contact або створює новий.
    """
    chat, _ = Chat.objects.get_or_create(
        user=user,
        contact=contact,
        defaults={
            "title": f"Viber: {contact.first_name}",
            # додайте інші обовʼязкові поля моделі Chat
        }
    )
    return chat

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def echat_viber_webhook(request):
    data = json.loads(request.body or '{}')
    logger.debug("E-chat RAW: %s", data)

    # 1️⃣ службовий номер компанії, кому прийшло
    service_number = data.get('number')
    if not service_number:
        return Response({'error': 'no service number'}, status=400)

    try:
        user = CustomUser.objects.get(echat_instance_id=service_number)
    except CustomUser.DoesNotExist:
        return Response({'error': 'unknown service number'}, status=404)

    # 2️⃣ номер клієнта
    raw_client_number = data.get('contact', {}).get('number')
    client_number = normalize_phone_number(raw_client_number)
    if not client_number:
        return Response({'error': 'bad client number'}, status=400)

    # 3️⃣ ContactPhone + Contact
    contact_phone, _ = ContactPhone.objects.get_or_create(phone=client_number)

    if contact_phone.contact is None:      # ще нема контакту – створюємо
        contact = Contact.objects.create(first_name=client_number)
        contact_phone.contact = contact
        contact_phone.save(update_fields=['contact'])
    else:
        contact = contact_phone.contact

    chat = get_or_create_chat(user, contact)

    sender = 'contact' if data.get('direction') == 'incoming' else 'user'

    # 4️⃣  створюємо НОВУ Interaction для кожного повідомлення
    inter = Interaction.objects.create(
        user=user,
        chat=chat,
        contact=contact,
        contact_phone=contact_phone,
        date=timezone.now(),
        interaction_type='viber',
        sender=sender,
        description='',
        is_read=(sender == 'user')  # ← для власних вихідних одразу «прочитано»
    )

    # 5️⃣ Зберігаємо повідомлення
    msg = data.get('message', {})
    ViberMessage.objects.create(
        interaction=inter,
        contact=contact,
        contact_phone=contact_phone,
        user=user,
        text=msg.get('text', ''),
        media_url=msg.get('file'),
        media_type=msg.get('type') if msg.get('type') != 'text' else None,
        echat_message_id=msg.get('message_id'),
        delivery_status=('delivered' if data.get('direction') == 'incoming'
                         else 'sent'),
        raw_event=data,
        date=timezone.now(),
    )

    # позначаємо, що в цього номера точно є Viber
    if not contact_phone.has_viber or not contact_phone.viber_id:
        contact_phone.has_viber = True
        contact_phone.viber_id = raw_client_number
        contact_phone.viber_name = data.get('contact', {}).get('name')
        contact_phone.save(update_fields=['has_viber', 'viber_id', 'viber_name'])

    # Надсилаємо сповіщення про нову взаємодію
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{chat.id}',
        {
            'type': 'update_interaction',
            'interaction_id': inter.id,
        }
    )

    # Надсилаємо сповіщення про оновлення списку чатів
    async_to_sync(channel_layer.group_send)(
        f'user_{user.id}_chats',
        {'type': 'update_chats'}
    )

    # Надсилаємо пуш-сповіщення
    if data.get('direction') == 'incoming':  # Вхідний дзвінок
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}_notifications',
            {
                'type': 'show_notification',
                'chat_id': chat.id,
                'contact_name': f"{contact.first_name} {contact.last_name or ''}",
                'company_name': contact.company.name if contact.company else '',
                'message': 'Viber повідомлення'
            }
        )

    return Response({'ok': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def echat_viber_status(request):
    """
    Web-hook для статусів вихідних повідомлень E-Chat.
    Тіло webhook-а згідно з docs:
    {
      "event": "outgoing_message_status",
      "messenger": "viber",
      "message_id": "...",        # наш ext_id
      "status": "1|2|3|4|5|6|7",
      "description": "..."
    }
    """
    data        = request.data
    mid         = str(data.get("message_id", ""))      # string!
    status_code = str(data.get("status", ""))
    descr       = data.get("description", "")

    status_map = {
        "1": "delivered",
        "2": "failed",
        "3": "failed",
        "4": "failed",
        "5": "pending",     # still waiting
        "6": "failed",
        "7": "failed",
    }

    try:
        msg = ViberMessage.objects.select_related('user', 'contact_phone', 'interaction').get(
            echat_message_id=mid
        )
    except ViberMessage.DoesNotExist:
        return Response({"error": "unknown message_id"}, status=404)

    # 1️⃣  оновлюємо сам ViberMessage
    msg.delivery_status = status_map.get(status_code, "failed")
    msg.error_code      = f"{status_code}: {descr}"
    msg.raw_event       = data
    msg.save(
        update_fields=['delivery_status', 'error_code', 'raw_event']
    )

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f'chat_{msg.interaction.chat.id}',
        {
            'type': 'update_interaction',
            'interaction_id': msg.interaction.id,
        }
    )


    if status_code != "1":  # 1 = delivered, решта = проблема


        async_to_sync(channel_layer.group_send)(
            f'user_{msg.user.id}_notifications',
            {
                'type': 'show_notification',
                'chat_id': msg.interaction.chat.id,
                'contact_name': f"{msg.contact_phone.contact.first_name} {msg.contact_phone.contact.last_name or ''}",
                'company_name': msg.contact_phone.contact.company.name if msg.contact_phone.contact.company else '',
                'message': '❗️❗️❗️Повідомлення не надіслано❗️❗️❗️'
            }
        )

    # 2️⃣  якщо «2 — номер не в Viber» → ставимо has_viber = False
    if status_code == "2" and msg.contact_phone:
        if msg.contact_phone.has_viber:                # щоб не писати зайвий UPDATE
            msg.contact_phone.has_viber = False
            msg.contact_phone.save(update_fields=['has_viber'])

    return Response({"ok": True})

