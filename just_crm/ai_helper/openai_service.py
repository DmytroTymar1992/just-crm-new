import json, openai, re
from django.conf import settings
from django.utils import timezone
from tiktoken import get_encoding
from chats.models import Interaction
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)
ENC = get_encoding("cl100k_base")                # токенізатор OpenAI

def _format(i: Interaction) -> str:
    ts = i.date.strftime("%d.%m.%Y %H:%M")        # 06.06.2025 10:15
    who = "менеджера" if i.sender == "user" else "клієнта"

    match i.interaction_type:
        case Interaction.InteractionType.CALL:
            call = i.calls.first()
            body = (call.result or call.description or "").strip()
            return f"Взаємодія {ts} • дзвінок від {who}. Результат: {body[:800]}"

        case Interaction.InteractionType.EMAIL:
            em = i.emails.first()
            subj = em.subject if em else ""
            return (f"Взаємодія {ts} • лист {who}. Тема: {subj[:120]}. "
                    f"Текст: {(em.body if em else '')[:400]}")

        case Interaction.InteractionType.TELEGRAM:
            t = i.telegram_messages.first()
            return f"Взаємодія {ts} • повідомлення Telegram {who}. Текст: {(t.text if t else '')[:400]}"

        case Interaction.InteractionType.VIBER:
            v = i.viber_messages.first()
            return f"Взаємодія {ts} • повідомлення Viber {who}. Текст: {(v.text if v else '')[:400]}"

        case _:
            return f"Взаємодія {ts} • {i.interaction_type}. Опис: {i.description[:400]}"

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
          .order_by('-date')[:10])

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
        Відавай перевагу дзвінкам якщо іншого не передбачино логічно по історії взаємодій менеджера та клієнта.
        В goal старайся не вказувати дієслова які вказують на тип задачі. це й так зрозуміло з типу задачі.
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
