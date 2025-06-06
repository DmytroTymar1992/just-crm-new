import json, openai, re
from django.conf import settings
from django.utils import timezone
from tiktoken import get_encoding
from chats.models import Interaction
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)
ENC = get_encoding("cl100k_base")                # токенізатор OpenAI

def _format(i: Interaction) -> str:
    """Перетворює Interaction + дочірню модель у компактний текст."""
    ts = i.date.strftime("%Y-%m-%d %H:%M")

    if i.interaction_type == Interaction.InteractionType.CALL:
        call = i.calls.first()
        body = (call.description or call.result or "")[:2500]
        return f"[CALL {ts}] {i.sender}: {body}"

    if i.interaction_type == Interaction.InteractionType.EMAIL:
        em = i.emails.first()
        body = em.body[:2500] if em else ""
        subj = em.subject if em else ""
        return f"[EMAIL {ts}] {i.sender}: subj “{subj}” {body}"

    if i.interaction_type == Interaction.InteractionType.TELEGRAM:
        msg = i.telegram_messages.first()
        return f"[TG {ts}] {i.sender}: {msg.text[:2500] if msg else ''}"

    if i.interaction_type == Interaction.InteractionType.VIBER:
        msg = i.viber_messages.first()
        return f"[VB {ts}] {i.sender}: {msg.text[:2500] if msg else ''}"

    return f"[{i.interaction_type.upper()} {ts}] {i.sender}: {i.description[:500]}"

def _limit_tokens(text: str, max_tok: int = 3500) -> str:
    toks = ENC.encode(text)
    if len(toks) <= max_tok:
        return text
    # обрізаємо початок (залишаємо останні max_tok)
    return ENC.decode(toks[-max_tok:])

def suggest_task(interaction: Interaction) -> dict:
    """Генерує {type, goal, short_description} на базі історії чату."""
    qs = (Interaction.objects
          .filter(chat=interaction.chat)
          .select_related('user', 'contact')
          .prefetch_related('calls', 'emails',
                            'telegram_messages', 'viber_messages')
          .order_by('-date')[:100])

    history = "\n".join(reversed([_format(i) for i in qs]))
    history = _limit_tokens(history)             # захист від >8К токенів

    system_msg = (
                """
        Ти — асистент CRM. 
        В CRM Менеджери спілкуютсья з клієнтами та пропонують послуги розміщення вакансій на Джоп сайті JUST-look
        Твоє завдання:
        
        1. Прочитати історію (найсвіжіша взаємодія внизу).
        2. Знайти, ЩО саме менеджер пообіцяв зробити клієнту 🌟
           або яку явну дію попросив сам клієнт.
        3. Менеджер може поставити собі задачу Дзвінок, Лист (це Email лист) або повідомлення ( це Viber або Telegram повідомлення)  
        4. Запропонуй менеджеру варіант наступної задачі по цьому клієнту в форматі type, goal, short_description  
        5. Повернути ТІЛЬКИ JSON:
        {
         "type": "Дзвінок | лист | повідомлення",
         "goal": "коротке дієслово + об'єкт",
         "short_description": "1–2 речення (уточнення)"
        }
        
        Якщо жодна дія не озвучена — запропонуй логічний follow-up.
        Dідавай перевагу дзвінкам якщо іншого не передбачино логічно по історії взаємодій менеджера та клієнта.
        """
    )
    user_msg = f"Історія:\n{history}\n\nЯку задачу потрібно створити?"

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,  # "gpt-4o-mini"
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=120,
        timeout=settings.OPENAI_TIMEOUT,
    )

    content = response.choices[0].message.content
    return json.loads(content)
