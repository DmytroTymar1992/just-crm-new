# ai_helper/tasks.py
from celery import shared_task
from django.apps import apps
from django.db import transaction
from django.utils import timezone
import logging
from .openai_service import suggest_task
from .models import AiSuggestion
from django.conf import settings
from calls.models import Call
import json
from openai import OpenAI
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


Interaction = apps.get_model("chats", "Interaction")
logger = logging.getLogger(__name__)

def load_result_options_from_file(path='ai_helper/data/call_results_list.txt'):
    try:
        with open(path, encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return lines
    except Exception as e:
        logger.error(f"Не вдалося завантажити список результатів: {e}", exc_info=True)
        return []

def build_gpt_prompt(transcript):
    result_options = load_result_options_from_file()
    options_text = "\n".join(result_options)

    system_prompt = (
        "Ти — CRM-асистент. Тобі надається транскрипція дзвінка з клієнтом. "
        "Твоя задача —:\n"
        "1. Визначити *результат дзвінка* — одну фразу зі списку нижче.\n"
        "2. Сформулювати короткий опис розмови (1-3 речення).\n\n"
        "💡 Обов’язково поверни відповідь у **точному JSON-форматі**:\n"
        "{ \"result\": \"...\", \"description\": \"...\" }\n\n"
        "Не пиши нічого поза межами JSON. Результат має бути однією фразою з цього списку:\n"
        f"{options_text}"
    )

    user_prompt = f"""Ось транскрипція розмови:
{transcript}

Виконай інструкцію вище.
"""

    return system_prompt, user_prompt

@shared_task
def analyze_transcription_result(call_id):
    try:
        call = Call.objects.get(pk=call_id)
        if not call.transcription:
            logger.warning(f"Call {call_id} has no transcription.")
            return

        system_prompt, user_prompt = build_gpt_prompt(call.transcription)

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        logger.debug(f"Raw GPT response for call {call_id}: {raw}")

        parsed = json.loads(raw)

        call.result = parsed.get("result")
        call.description = parsed.get("description")
        call.save()
        logger.info(f"Saved GPT result for call {call_id}: {call.result}")

        # 🔄 WebSocket: оновлення інтерфейсу
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{call.interaction.chat_id}",
            {
                "type": "open_call_result_modal",
                "call_id": call.id,
                "result": call.result,
                "description": call.description or "",
                "loading": False
            },
        )
        logger.info(f"Sent WebSocket update for call {call.id} with GPT result.")

    except json.JSONDecodeError:
        logger.error(f"Не вдалося розпарсити JSON від GPT для call {call_id}", exc_info=True)
    except Exception as e:
        logger.error(f"Помилка GPT аналізу call {call_id}: {e}", exc_info=True)




@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_task_for_interaction(self, interaction_id: int):
    try:
        interaction = (
            Interaction.objects
            .select_related("chat", "contact", "user")
            .get(pk=interaction_id)
        )

        # 1. дістаємо пропозицію від GPT-4o
        data = suggest_task(interaction)          # {'type': …, 'goal': …, 'short_description': …}

        # 2. один запис на чат → оновлюємо або створюємо
        with transaction.atomic():
            AiSuggestion.objects.update_or_create(
                chat=interaction.chat,            # ключ (OneToOne primary_key)
                defaults={
                    "contact":           interaction.contact,
                    "user":              interaction.user,
                    "type":              data["type"],
                    "goal":              data["goal"],
                    "short_description": data["short_description"],
                    "updated_at":        timezone.now(),
                },
            )

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
