# ai_helper/tasks.py
from celery import shared_task
from django.apps import apps
from django.db import transaction
from django.utils import timezone

from .openai_service import suggest_task
from .models import AiSuggestion

Interaction = apps.get_model("chats", "Interaction")


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
