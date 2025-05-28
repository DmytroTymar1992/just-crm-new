import json, logging, requests
from celery import shared_task
from django.conf import settings
from .models import TelegramMessage
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

log = logging.getLogger("sales_telegram.api")

SEND_URL = getattr(
    settings,
    "ECHAT_TELEGRAM_SEND_URL",
    "https://telegrame.e-chat/api",
)

@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=120)
def send_telegram_message(self, msg_id: int):
    msg = (
        TelegramMessage.objects
        .select_related('user', 'contact_phone', 'interaction')
        .get(pk=msg_id)
    )

    ext_id = str(msg.pk)
    if msg.echat_message_id != ext_id:
        msg.echat_message_id = ext_id
        msg.save(update_fields=["echat_message_id"])

    payload = {
        "bot_id": msg.user.echat_instance_id,
        "message": {"id": ext_id, "text": msg.text},
        "contact": {"telegram_id": msg.contact_phone.telegram_id if msg.contact_phone else ''},
    }
    headers = {
        "Api-Key": msg.user.echat_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    log.debug("→ E-chat payload %s", json.dumps(payload, ensure_ascii=False))
    r = requests.post(SEND_URL, json=payload, headers=headers, timeout=10)
    log.debug("← E-chat %s %s", r.status_code, r.text.strip())
    r.raise_for_status()

    data = r.json()
    if data.get("status") != "Success":
        raise Exception(f"E-chat error: {data}")

    msg.delivery_status = "sent"
    msg.raw_event = data
    msg.save(update_fields=["delivery_status", "raw_event"])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{msg.user.id}_chats',
        {'type': 'update_chats'}
    )
    async_to_sync(channel_layer.group_send)(
        f'chat_{msg.interaction.chat.id}',
        {
            'type': 'update_interaction',
            'interaction_id': msg.interaction.id,
        }
    )