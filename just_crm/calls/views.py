from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
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
from django.contrib.auth.decorators import login_required
import logging
from .tasks import transcribe_call


logger = logging.getLogger(__name__)

def _get_user_and_contact(data):
    """Допоміжна функція для отримання або створення користувача та контакту."""
    leg = data.get('leg', {})
    leg_ext = leg.get('ext')
    other_legs = data.get('otherLegs', [])
    other_leg_num = other_legs[0].get('num') if other_legs else None

    user = CustomUser.objects.filter(phonet_extension=leg_ext).first()
    if not user:
        return None, None, JsonResponse({'error': f'User with extension {leg_ext} not found'}, status=400)

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
        return user, None, JsonResponse({'error': 'Contact not found and cannot be created for internal call'}, status=400)

    return user, (contact, contact_phone), None

def _create_or_get_chat(user, contact):
    """Допоміжна функція для створення або отримання чату."""
    chat, created = Chat.objects.get_or_create(
        user=user,
        contact=contact,
        defaults={'created_at': timezone.now()}
    )
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}_chats',
            {'type': 'update_chats'}
        )
    return chat

def _get_sender_and_user_names(data, user):
    """Допоміжна функція для визначення відправника та імені користувача."""
    lg_direction = data.get('lgDirection')
    if lg_direction == 2:
        sender = Interaction.SenderType.USER
        user_last_name = user.last_name if user.last_name else user.first_name
        user_first_name = user.first_name if user.first_name else user.last_name
    elif lg_direction == 4:
        sender = Interaction.SenderType.CONTACT
        user_last_name = ''
        user_first_name = ''
    else:
        sender = Interaction.SenderType.SYSTEM
        user_last_name = ''
        user_first_name = ''
    return sender, user_first_name, user_last_name

@login_required
@require_GET
def get_call_details(request, call_id):
    """Return JSON with call description and result."""
    try:
        call = Call.objects.get(id=call_id)
        return JsonResponse({
            'status': 'success',
            'description': call.description or '',
            'result': call.result or ''
        })
    except Call.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Call not found'
        }, status=404)

@csrf_exempt
@require_POST
def phonet_dial_webhook(request):
    """Обробка події call.dial - створення нового дзвінка."""
    try:
        data = json.loads(request.body)
        if data.get('event') != 'call.dial':
            return JsonResponse({'status': 'ignored'}, status=200)

        uuid = data.get('uuid')
        parent_uuid = data.get('parentUuid')
        dial_at = data.get('dialAt')
        lg_direction = data.get('lgDirection')
        leg = data.get('leg', {})
        leg_id = leg.get('id')
        leg_ext = leg.get('ext')
        leg_name = leg.get('displayName')

        start_time = datetime.fromtimestamp(dial_at / 1000, tz=pytz.UTC) if dial_at else None

        with transaction.atomic():
            user, contact_data, error_response = _get_user_and_contact(data)
            if error_response:
                return error_response
            contact, contact_phone = contact_data

            chat = _create_or_get_chat(user, contact)
            sender, user_first_name, user_last_name = _get_sender_and_user_names(data, user)

            interaction = Interaction.objects.create(
                user=user,
                chat=chat,
                contact=contact,
                contact_phone=contact_phone,
                contact_email=None,
                date=timezone.now(),
                interaction_type=Interaction.InteractionType.CALL,
                sender=sender,
                user_last_name=user_last_name,
                user_first_name=user_first_name,
                description="Phonet call event: call.dial",
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
                date=timezone.now(),
                description="Phonet call event: call.dial"
            )

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat.id}',
                {
                    'type': 'update_interaction',
                    'interaction_id': interaction.id,
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}_chats',
                {'type': 'update_chats'}
            )

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

            logger.info(f"Created call with UUID {uuid}")
            return JsonResponse({'status': 'success'}, status=200)

    except Exception as e:
        logger.error(f"Error in phonet_dial_webhook: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_POST
def phonet_bridge_webhook(request):
    """Обробка події call.bridge - оновлення дзвінка (підняття слухавки)."""
    try:
        data = json.loads(request.body)
        if data.get('event') != 'call.bridge':
            return JsonResponse({'status': 'ignored'}, status=200)

        uuid = data.get('uuid')
        bridge_at = data.get('bridgeAt')

        answer_time = datetime.fromtimestamp(bridge_at / 1000, tz=pytz.UTC) if bridge_at else None

        with transaction.atomic():
            call = Call.objects.filter(phonet_uuid=uuid).first()
            if not call:
                logger.warning(f"No call found with phonet_uuid={uuid}")
                return JsonResponse({'error': f'Call with UUID {uuid} not found'}, status=400)

            user, contact_data, error_response = _get_user_and_contact(data)
            if error_response:
                return error_response
            contact, contact_phone = contact_data

            call.answer_time = answer_time
            call.description = "Phonet call event: call.bridge"
            call.contact_phone = contact_phone
            call.save()

            chat = _create_or_get_chat(user, contact)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat.id}',
                {
                    'type': 'update_interaction',
                    'interaction_id': call.interaction.id,
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}_chats',
                {'type': 'update_chats'}
            )

            logger.info(f"Updated call with UUID {uuid} for bridge event")
            return JsonResponse({'status': 'success'}, status=200)

    except Exception as e:
        logger.error(f"Error in phonet_bridge_webhook: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_POST
def phonet_hangup_webhook(request):
    """Обробка події call.hangup - оновлення дзвінка (завершення)."""
    try:
        data = json.loads(request.body)
        if data.get('event') != 'call.hangup':
            return JsonResponse({'status': 'ignored'}, status=200)

        uuid = data.get('uuid')
        server_time = data.get('serverTime')
        account_domain = data.get('accountDomain')

        end_time = datetime.fromtimestamp(server_time / 1000, tz=pytz.UTC) if server_time else None
        recording_link = f"https://{account_domain}/rest/public/calls/{uuid}/audio" if account_domain else None

        with transaction.atomic():
            call = Call.objects.filter(phonet_uuid=uuid).select_for_update().first()
            if not call:
                logger.warning(f"No call found with phonet_uuid={uuid}")
                return JsonResponse({'error': f'Call with UUID {uuid} not found'}, status=400)

            user, contact_data, error_response = _get_user_and_contact(data)
            if error_response:
                return error_response
            contact, contact_phone = contact_data

            # Оновлюємо поля дзвінка
            call.end_time = end_time
            call.recording_link = recording_link
            call.description = "Phonet call event: call.hangup"
            call.contact_phone = contact_phone
            call.save()

            # Оновлюємо об’єкт із бази, щоб отримати актуальний стан
            call.refresh_from_db()
            logger.info(f"Call UUID: {uuid}, answer_time: {call.answer_time}, end_time: {call.end_time}, interaction chat_id: {call.interaction.chat_id}")

            chat = _create_or_get_chat(user, contact)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat.id}',
                {
                    'type': 'update_interaction',
                    'interaction_id': call.interaction.id,
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}_chats',
                {'type': 'update_chats'}
            )

            # Перевіряємо answer_time після оновлення
            #if call.answer_time:
            #    logger.info(f"Opening call result modal for call ID: {call.id}")
            #    async_to_sync(channel_layer.group_send)(
            #        f'chat_{call.interaction.chat_id}',
            #        {
            #            'type': 'open_call_result_modal',
            #            'call_id': call.id
            #        }
            #    )
            #else:
            #    logger.info(f"Modal not opened for call UUID: {uuid}, answer_time is None")

            if recording_link:
                logger.debug(f"Scheduling transcription task for call ID {call.id}")
                transcribe_call.delay(call.id, recording_link)

            logger.info(f"Updated call with UUID {uuid} for hangup event")
            return JsonResponse({'status': 'success'}, status=200)

    except Exception as e:
        logger.error(f"Error in phonet_hangup_webhook: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def update_call_result(request):
    try:
        call_id = request.POST.get('call_id')
        result = request.POST.get('result')
        description = request.POST.get('description')

        call = Call.objects.get(id=call_id)
        call.result = result
        call.description = description
        call.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Call updated successfully'
        })
    except Call.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Call not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)