from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from chats.models import Chat, Interaction
from contacts.models import Contact
from django.db.models import Max
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from tasks.models import Task
from datetime import date
from itertools import chain
from .models import Chat
from vacancies.models import Vacancy
from django.template.loader import render_to_string
from django.db.models import Max, Count, Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from collections import defaultdict
from django.utils import timezone
from datetime import timedelta


def group_interactions_by_date(interactions):
    grouped = defaultdict(list)
    for interaction in interactions:
        # приводимо до локального часу й беремо лише дату
        day = timezone.localtime(interaction.date).date()
        grouped[day].append(interaction)
    return grouped

@login_required
def chat_view(request, chat_id=None):
    """
    View-функція для обробки запитів, пов'язаних із переглядом чатів користувача.

    Ця функція відповідає за отримання списку чатів, їх сортування,
    завантаження повідомлень з обраного чату та побудову інтерфейсу з можливістю
    підвантаження даних через AJAX-запити.

    Parameters:
        request (HttpRequest): HTTP-запит від користувача, який містить інформацію
        про тип запиту, параметри, дані користувача тощо.
        chat_id (Optional[int]): Ідентифікатор обраного чату. Якщо значення None,
        обраний чат не завантажується.

    Raises:
        Http404: Піднімається, якщо обраний чат з id, наданим у chat_id, не знайдений
        для поточного користувача.

    Returns:
        HttpResponse: Відповідь, що містить HTML-сторінку чату або JsonResponse для
        AJAX-запиту, яка містить HTML-фрагмент і метадані для таблиці повідомлень
        в обраному чаті.
    """
    # Сортуємо чати за датою останньої взаємодії або created_at
    chats = Chat.objects.filter(user=request.user).select_related('contact').annotate(
        last_interaction=Max('interactions__date'),
        unread_count=Count('interactions', filter=Q(interactions__is_read=False, interactions__sender='contact'))
    ).order_by('-last_interaction', '-created_at')[:20]

    selected_chat = None
    interactions = []
    page_obj = None
    selected_task = None
    selected_task_status = None
    contact_phones = []

    if chat_id:
        selected_chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        # Отримуємо взаємодії, впорядковані за датою (від старіших до новіших)
        interaction_qs = Interaction.objects.filter(chat=selected_chat).select_related(
            'contact', 'contact_phone', 'contact_email'
        ).order_by('date')

        selected_task = Task.objects.filter(
            user=request.user,
            contact=selected_chat.contact,
            is_completed=False
        ).first()

        if selected_task:
            today = date.today()
            task_date = selected_task.task_date.date()
            if task_date < today:
                selected_task_status = "overdue"
            elif task_date == today:
                selected_task_status = "today"
            else:
                selected_task_status = "future"

        contact_phones = selected_chat.contact.phones.all()

        paginator = Paginator(interaction_qs, 10)
        last_page = paginator.num_pages

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # AJAX-запит — звичайна пагінація (одна сторінка)
            page_number = int(request.GET.get('page', last_page))
            page_obj = paginator.get_page(page_number)
            interactions = page_obj.object_list

            grouped = group_interactions_by_date(interactions)
            sorted_days = sorted(grouped.keys())
            grouped_list = [(day, grouped[day]) for day in sorted_days]

            html = render_to_string(
                'chats/partial_grouped_messages.html',
                {'grouped_interactions': grouped_list},
                request=request
            )
            return JsonResponse({
                'html': html,
                'has_previous': page_obj.has_previous(),
                'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
            })
        else:
            # Початкове завантаження — дві останні сторінки
            if last_page == 1:
                page_obj = paginator.get_page(last_page)
                interactions = page_obj.object_list
            else:
                last_page_obj = paginator.get_page(last_page)
                prev_page_obj = paginator.get_page(last_page - 1)
                # об'єднуємо обидві сторінки
                interactions = list(chain(prev_page_obj.object_list, last_page_obj.object_list))
                # для пагінації повертаємо останню (використається при подальших AJAX-запитах)
                page_obj = last_page_obj

    for chat in chats:
        chat.avatar_color = (chat.id % 8) or 8

    grouped = group_interactions_by_date(interactions)
    sorted_days = sorted(grouped.keys())
    grouped_list = [(day, grouped[day]) for day in sorted_days]

    context = {
        'chats': chats,
        'selected_chat': selected_chat,
        'grouped_interactions': grouped_list,
        'page_obj': page_obj,
        'selected_task': selected_task,
        'selected_task_status': selected_task_status,
        'contact_phones': contact_phones,

    }
    return render(request, 'chats/chat.html', context)


@login_required
def send_message(request, chat_id):
    """
    Функція для відправки повідомлення у чат, який належить поточному користувачеві. Створює взаємодію,
    пов’язану з телеграм-комунікацією, і надсилає відповідні сповіщення через WebSocket канал.

    Args:
        request (HttpRequest): HTTP-запит, який включає POST-дані користувача.
        chat_id (int): Ідентифікатор чату, до якого надсилається повідомлення.

    Returns:
        HttpResponse: Перенаправлення користувача на сторінку деталей чату.
    """
    if request.method == 'POST':
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        description = request.POST.get('description')
        if description:
            interaction = Interaction.objects.create(
                user=request.user,
                chat=chat,
                contact=chat.contact,
                interaction_type='telegram',
                sender='user',
                description=description,
            )
            channel_layer = get_channel_layer()
            # Надсилаємо сповіщення про нову взаємодію
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat.id}',
                {
                    'type': 'update_interaction',
                    'interaction_id': interaction.id,
                }
            )
            # Надсилаємо сповіщення про оновлення списку чатів
            async_to_sync(channel_layer.group_send)(
                f'user_{request.user.id}_chats',
                {'type': 'update_chats'}
            )
    return redirect(reverse('chat_detail', args=[chat_id]))


@login_required
def get_company_vacancies_html(request, chat_id):
    try:
        chat = Chat.objects.select_related('contact__company').get(id=chat_id, user=request.user)
        company = chat.contact.company
        if not company:
            return JsonResponse({'html': '<p>Компанія не вказана</p>'})

        vacancies = Vacancy.objects.filter(
            company=company,
            is_active=True,
            work_id__isnull=False
        ).exclude(work_id='')

        html = render_to_string('partials/_vacancy_card.html', {'vacancies': vacancies})
        return JsonResponse({'html': html})
    except Chat.DoesNotExist:
        return JsonResponse({'html': '<p>Чат не знайдено</p>'}, status=404)


@login_required
def get_chat_list_html(request):
    selected_chat_id = request.GET.get('selected_chat_id')
    try:
        selected_chat_id = int(selected_chat_id)
    except (TypeError, ValueError):
        selected_chat_id = None

    chats = Chat.objects.filter(user=request.user).select_related('contact', 'contact__company').annotate(
        last_interaction=Max('interactions__date'),
        unread_count=Count('interactions', filter=Q(interactions__is_read=False, interactions__sender='contact'))
    ).order_by('-last_interaction', '-created_at')

    for chat in chats:
        chat.avatar_color = (chat.id % 8) or 8

    html = render_to_string('partials/chat_item.html', {
        'chats': chats,
        'selected_chat': Chat(id=selected_chat_id) if selected_chat_id else None
    }, request=request)

    return JsonResponse({'html': html})


@csrf_exempt
@require_POST
def mark_interaction_read(request):
    try:
        data = json.loads(request.body)
        interaction_id = data.get('interaction_id')
        if not interaction_id:
            return JsonResponse({'error': 'Missing interaction_id'}, status=400)

        interaction = Interaction.objects.get(id=interaction_id)
        interaction.is_read = True
        interaction.save(update_fields=['is_read'])

        chat = interaction.chat

        channel_layer = get_channel_layer()
        # Надсилаємо сповіщення про оновлення списку чатів
        async_to_sync(channel_layer.group_send)(
            f'user_{request.user.id}_chats',
            {'type': 'update_chats'}
        )

        return JsonResponse({'status': 'ok'})
    except Interaction.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



#import requests
#from django.http import StreamingHttpResponse
#import logging
#logger = logging.getLogger(__name__)  # вгорі файлу

#@csrf_exempt
#def gpt_completion_simple(request):
#    if request.method != "POST":
#        return JsonResponse({'error': 'Only POST allowed'}, status=405)
#
#    try:
#        data = json.loads(request.body)
#        user_input = data.get("prompt", "").strip()
#
#        if not user_input:
#            return JsonResponse({'error': 'Empty prompt'}, status=400)
#
#        # 🧠 Формуємо промт — ШІ має лише *продовжити думку*, не пояснювати!
#        system_prompt = (
#            "Ти CRM-асистент, який допомагає менеджеру з продажів швидко дописувати повідомлення клієнтам. "
#            "Менеджера звати Дмитро"
#            "Менеджер працює в компанії JUST-look - це сайт з пошуку роботи та розміщеня вакансій"
#            "Клієнти менеджера це роботодавці які потенційно можуть розміщувати вакансії"
#            "Отримуєш лише частину фрази, яку менеджер щойно почав писати. "
#            "Твоя задача — логічно продовжити цю думку без зміни теми і без зайвих пояснень. "
#            "Відповідай коротко, природною українською мовою — так, ніби це написав менеджер."
#        )
#
#        headers = {
#            "Authorization": "Bearer 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",
#            "Content-Type": "application/json",
#            "HTTP-Referer": "https://just-crm.online",       # 🔗 для рейтингу OpenRouter (необов'язково)
#            "X-Title": "Just CRM Autocomplete"              # 🔖 назва проекту
#        }
#
#        payload = {
#            "model": "openai/gpt-4.1-mini",
#            "messages": [
#                {"role": "system", "content": system_prompt},
#                {"role": "user", "content": user_input}
#            ],
#            "temperature": 0.4,
#            "max_tokens": 30
#        }
#
#        response = requests.post(
#            "https://openrouter.ai/api/v1/chat/completions",
#            headers=headers,
#            json=payload,
#            timeout=5
#        )
#
#        response.raise_for_status()
#        res_json = response.json()
#
#        content = res_json.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
#        return JsonResponse({"response": content})
#
#    except requests.exceptions.HTTPError as http_err:
#        logger.error("HTTP error: %s", http_err.response.text)
#        return JsonResponse({"error": f"HTTP error: {http_err.response.text}"}, status=http_err.response.status_code)
#
#    except Exception as e:
#        import traceback
#        logger.error("GPT error: %s", traceback.format_exc())
#        return JsonResponse({"error": "Internal error"}, status=500)