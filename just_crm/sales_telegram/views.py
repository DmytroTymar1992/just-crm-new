import json
import logging
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
from chats.models import Interaction, Chat
from .models import TelegramMessage

logger = logging.getLogger(__name__)

def get_or_create_chat(user: CustomUser, contact: Contact) -> Chat:
    chat, _ = Chat.objects.get_or_create(
        user=user,
        contact=contact,
        defaults={
            "title": f"Telegram: {contact.first_name}",
        }
    )
    return chat

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def echat_telegram_webhook(request):
    data = json.loads(request.body or '{}')
    logger.debug("E-chat Telegram RAW: %s", data)

    # 1️⃣ Номер бота (аналог echat_instance_id_telegram)
    number = data.get('number')
    if not number:
        return Response({'error': 'no number'}, status=400)

    try:
        user = CustomUser.objects.get(echat_instance_id_telegram=number)
    except CustomUser.DoesNotExist:
        return Response({'error': 'unknown number'}, status=404)

    # 2️⃣ Telegram ID контакту (sender.id)
    telegram_id = data.get('sender', {}).get('id')
    if not telegram_id:
        return Response({'error': 'bad sender id'}, status=400)

    # 3️⃣ ContactPhone + Contact
    contact_phone = None
    raw_phone = data.get('sender', {}).get('phone')
    if raw_phone:
        client_number = normalize_phone_number(raw_phone)
        contact_phone, _ = ContactPhone.objects.get_or_create(phone=client_number)

    if contact_phone and contact_phone.contact:
        contact = contact_phone.contact
    else:
        contact_name = data.get('sender', {}).get('name') or telegram_id
        contact = Contact.objects.create(first_name=contact_name)
        if contact_phone:
            contact_phone.contact = contact
            contact_phone.save(update_fields=['contact'])

    chat = get_or_create_chat(user, contact)

    sender = 'contact' if data.get('direction') == 'incoming' else 'user'

    # 4️⃣ Створюємо Interaction
    inter = Interaction.objects.create(
        user=user,
        chat=chat,
        contact=contact,
        contact_phone=contact_phone,
        user_last_name=user.last_name,
        user_first_name=user.first_name,
        date=timezone.now(),
        interaction_type='telegram',
        sender=sender,
        description='',
        is_read=(sender == 'user')
    )

    # 5️⃣ Зберігаємо повідомлення
    msg = data.get('message', {})
    media_url = msg.get('media')
    media_type = msg.get('type') if msg.get('type') in ['text', 'media'] else None

    TelegramMessage.objects.create(
        interaction=inter,
        contact=contact,
        contact_phone=contact_phone,
        user=user,
        text=msg.get('text', ''),
        media_url=media_url,
        media_type=media_type,
        echat_message_id=msg.get('id'),
        delivery_status='delivered',
        raw_event=data,
        date=timezone.now(),
        error_code=None
    )

    # Оновлюємо інформацію про Telegram
    if contact_phone:
        contact_phone.has_telegram = True
        contact_phone.telegram_id = telegram_id
        contact_phone.telegram_username = data.get('sender', {}).get('username')
        contact_phone.save(update_fields=['telegram_id', 'telegram_username'])


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
                'message': 'Telegram повідомлення'
            }
        )

    return Response({'ok': True})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def echat_telegram_status(request):
    data = request.data
    mid = str(data.get("message_id", ""))
    status = str(data.get("delivery_status", ""))
    descr = data.get("description", "")

    try:
        msg = TelegramMessage.objects.select_related('user', 'contact_phone', 'interaction').get(
            echat_message_id=mid
        )
    except TelegramMessage.DoesNotExist:
        return Response({"error": "unknown message_id"}, status=404)

    # Оновлюємо статус
    if status == "1":
        msg.delivery_status = "delivered"
    elif status == "4":
        msg.delivery_status = "failed"
    else:
        logger.warning(f"Unknown delivery_status from E-Chat: {status}")
        msg.delivery_status = "failed"
    msg.error_code = descr if descr else None
    msg.raw_event = data
    msg.save(update_fields=['delivery_status', 'error_code', 'raw_event'])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{msg.interaction.chat.id}',
        {
            'type': 'update_interaction',
            'interaction_id': msg.interaction.id,
        }
    )

    if status != "1":
        async_to_sync(channel_layer.group_send)(
            f'user_{msg.user.id}_notifications',
            {
                'type': 'show_notification',
                'chat_id': msg.interaction.chat.id,
                'contact_name': f"{msg.contact_phone.contact.first_name if msg.contact_phone else ''} {msg.contact_phone.contact.last_name or ''}",
                'company_name': msg.contact_phone.contact.company.name if msg.contact_phone and msg.contact_phone.contact.company else '',
                'message': '❗️❗️❗️Повідомлення не надіслано❗️❗️❗️'
            }
        )



    return Response({'ok': True})