from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from django.db import transaction
import json
from datetime import datetime
import pytz
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Call
from main.models import CustomUser
from contacts.models import Contact, ContactPhone
from chats.models import Chat, Interaction
from companies.models import Company

@csrf_exempt
@require_POST
def phonet_webhook(request):
    try:
        data = json.loads(request.body)
        event = data.get('event')
        if event not in ['call.dial', 'call.bridge', 'call.hangup']:
            return JsonResponse({'status': 'ignored'}, status=200)

        uuid = data.get('uuid')
        parent_uuid = data.get('parentUuid')
        dial_at = data.get('dialAt')
        bridge_at = data.get('bridgeAt')
        lg_direction = data.get('lgDirection')
        leg = data.get('leg', {})
        leg_id = leg.get('id')
        leg_ext = leg.get('ext')
        leg_name = leg.get('displayName')
        other_legs = data.get('otherLegs', [])
        other_leg_num = other_legs[0].get('num') if other_legs else None
        trunk_num = data.get('trunkNum')
        trunk_name = data.get('trunkName')

        start_time = datetime.fromtimestamp(dial_at / 1000, tz=pytz.UTC) if dial_at else None
        answer_time = datetime.fromtimestamp(bridge_at / 1000, tz=pytz.UTC) if bridge_at else None
        end_time = datetime.fromtimestamp(data.get('serverTime') / 1000, tz=pytz.UTC) if event == 'call.hangup' else None
        recording_link = f"https://{data.get('accountDomain')}/rest/public/calls/{uuid}/audio" if event == 'call.hangup' else None

        with transaction.atomic():
            user = CustomUser.objects.filter(phonet_extension=leg_ext).first()
            if not user:
                return JsonResponse({'error': f'User with extension {leg_ext} not found'}, status=400)

            contact_phone = None
            contact = None
            if other_leg_num:
                contact_phone = ContactPhone.objects.filter(phone=other_leg_num).first()
                if contact_phone:
                    contact = contact_phone.contact
                else:
                    first_name = other_legs[0].get('name') or other_leg_num if other_legs else other_leg_num or 'Unknown'
                    contact = Contact.objects.create(
                        company=None,
                        first_name=first_name,
                        last_name='',
                        position='',
                    )
                    contact_phone = ContactPhone.objects.create(
                        contact=contact,
                        phone=other_leg_num,
                        name='Основний'
                    )

            if not contact:
                return JsonResponse({'error': 'Contact not found and cannot be created for internal call'}, status=400)

            chat, created = Chat.objects.get_or_create(
                user=user,
                contact=contact,
                defaults={'created_at': timezone.now()}
            )
            if created:
                # Надсилаємо сповіщення про новий чат
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}_chats',
                    {'type': 'update_chats'}
                )

            if lg_direction == 2:
                sender = Interaction.SenderType.USER
            elif lg_direction == 4:
                sender = Interaction.SenderType.CONTACT
            else:
                sender = Interaction.SenderType.SYSTEM

            call = Call.objects.filter(phonet_uuid=uuid).first()

            if call:
                call.start_time = start_time or call.start_time
                call.answer_time = answer_time or call.answer_time
                call.end_time = end_time or call.end_time
                call.recording_link = recording_link or call.recording_link
                call.description = f"Phonet call event: {event}"
                call.contact_phone = contact_phone
                call.save()
            else:
                interaction = Interaction.objects.create(
                    user=user,
                    chat=chat,
                    contact=contact,
                    contact_phone=contact_phone,
                    contact_email=None,
                    date=timezone.now(),
                    interaction_type=Interaction.InteractionType.CALL,
                    sender=sender,
                    description=f"Phonet call event: {event}",
                    is_read=False
                )

                call = Call.objects.create(
                    phonet_uuid=uuid,
                    interaction=interaction,
                    parent_uuid=parent_uuid,
                    direction=lg_direction,
                    leg_id=leg_id,
                    leg_ext=leg_ext,
                    leg_name=leg_name,
                    contact=contact,
                    contact_phone=contact_phone,
                    start_time=start_time,
                    answer_time=answer_time,
                    end_time=end_time,
                    date=timezone.now(),
                    description=f"Phonet call event: {event}",
                    recording_link=recording_link
                )

            # Надсилаємо сповіщення про нову взаємодію
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat.id}',
                {
                    'type': 'update_interaction',
                    'interaction_id': interaction.id,
                }
            )

            # Надсилаємо сповіщення про оновлення списку чатів
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}_chats',
                {'type': 'update_chats'}
            )

            # Надсилаємо пуш-сповіщення
            if lg_direction == 4:  # Вхідний дзвінок
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}_notifications',
                    {
                        'type': 'show_notification',
                        'chat_id': chat.id,
                        'contact_name': f"{contact.first_name} {contact.last_name or ''}",
                        'company_name': contact.company.name if contact.company else '',
                        'message': 'Новий дзвінок'
                    }
                )

            return JsonResponse({'status': 'success'}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)