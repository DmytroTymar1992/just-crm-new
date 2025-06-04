from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Task, TaskTransfer, TasksMessage
from contacts.models import Contact
from chats.models import Chat, Interaction
from django.utils import timezone
from django.contrib import messages
from .forms import TaskForm, TaskTransferForm
from datetime import timedelta, datetime
from django.http import JsonResponse
import logging
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET


# Налаштування логування
logger = logging.getLogger(__name__)

@login_required
def kanban_board(request):
    return render(request, 'tasks/kanban_board.html', {})  # Лише рендеринг шаблону


@login_required
def kanban_tasks_api(request):
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    end_of_week = today + timedelta(days=(6 - today.weekday()))

    overdue = Task.objects.filter(
        user=request.user,
        is_completed=False,
        task_date__lt=today
    ).select_related('contact').order_by('task_date')

    today_tasks = Task.objects.filter(
        user=request.user,
        is_completed=False,
        task_date__gte=today,
        task_date__lt=tomorrow
    ).select_related('contact').order_by('task_date')

    tomorrow_tasks = Task.objects.filter(
        user=request.user,
        is_completed=False,
        task_date__gte=tomorrow,
        task_date__lt=tomorrow + timedelta(days=1)
    ).select_related('contact').order_by('task_date')

    this_week_tasks = Task.objects.filter(
        user=request.user,
        is_completed=False,
        task_date__gte=tomorrow + timedelta(days=1),
        task_date__lte=end_of_week
    ).select_related('contact').order_by('task_date')

    # Рендеринг HTML для кожної колонки
    overdue_html = render(request, 'tasks/task_list_partial.html', {'tasks': overdue}).content.decode('utf-8')
    today_html = render(request, 'tasks/task_list_partial.html', {'tasks': today_tasks}).content.decode('utf-8')
    tomorrow_html = render(request, 'tasks/task_list_partial.html', {'tasks': tomorrow_tasks}).content.decode('utf-8')
    this_week_html = render(request, 'tasks/task_list_partial.html', {'tasks': this_week_tasks}).content.decode('utf-8')

    data = {
        'overdue': overdue_html,
        'today': today_html,
        'tomorrow': tomorrow_html,
        'this_week': this_week_html,
    }
    return JsonResponse(data)



@login_required
def create_task(request):
    if request.method == 'POST':
        contact_id = request.POST.get('contact_id')
        if not contact_id:
            logger.error("No contact_id provided in POST request")
            return JsonResponse({'error': 'Контакт не вказано'}, status=400)

        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                contact = Contact.objects.get(id=contact_id)
                task = form.save(commit=False)
                task.user = request.user
                task.contact = contact
                task.save()
                return JsonResponse({'success': True})
            except Contact.DoesNotExist:
                logger.error(f"Contact not found: id={contact_id}")
                return JsonResponse({'error': 'Контакт не знайдено'}, status=400)
            except Exception as e:
                logger.error(f"Unexpected error in create_task: {str(e)}, POST data: {request.POST}", exc_info=True)
                return JsonResponse({'error': f'Невідома помилка: {str(e)}'}, status=500)
        else:
            logger.error(f"Form errors in create_task: {form.errors}")
            return JsonResponse({
                'error': 'Некоректні дані форми',
                'errors': form.errors.as_json(),
                'labels': {name: field.label for name, field in form.fields.items()}
            }, status=400)

    contact_id = request.GET.get('contact_id', '')
    if not contact_id:
        logger.error(f"No contact_id provided in GET request")
        return JsonResponse({'error': 'Contact ID не вказано'}, status=400)
    form = TaskForm(user=request.user)
    context = {
        'form': form,
        'contact_id': contact_id,
    }
    return render(request, 'tasks/task_form_contacts_modal.html', context)

@login_required
def create_task_in_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                task = form.save(commit=False)
                task.user = request.user
                task.contact = chat.contact
                task.save()

                user = request.user

                # Create Interaction with type 'system'
                interaction = Interaction.objects.create(
                    user=request.user,
                    contact=chat.contact,
                    interaction_type=Interaction.InteractionType.SYSTEM,
                    sender=Interaction.SenderType.SYSTEM,
                    description=f"Task created: {task.task_type} - {task.target}",
                    date=timezone.now(),
                    chat=chat
                )

                # Create TasksMessage
                TasksMessage.objects.create(
                    interaction=interaction,
                    contact=chat.contact,
                    type=TasksMessage.Type.CREATED,
                    task=task,
                    created_at=timezone.now()
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

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                messages.success(request, 'Задачу створено!')
                return redirect('kanban_board')
            except ValueError as e:
                logger.error(f"Error in create_task_in_chat: {str(e)}", exc_info=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Некоректні дані форми',
                        'errors': form.errors.as_json(),
                        'labels': {name: field.label for name, field in form.fields.items()}
                    }, status=400)
                messages.error(request, f'Помилка: {str(e)}')
        else:
            logger.error(f"Form errors in create_task_in_chat: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Некоректні дані форми', 'errors': form.errors.as_json()}, status=400)
            messages.error(request, 'Некоректні дані форми')
    form = TaskForm(user=request.user)
    context = {
        'form': form,
        'chat': chat,
    }
    return render(request, 'tasks/task_form_modal.html', context)


@login_required
@csrf_exempt
@require_POST
def complete_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id, user=request.user)
        task.is_completed = True
        task.completed_at = timezone.now()
        task.save()

        chat = Chat.objects.filter(user=request.user, contact=task.contact).first()
        user = request.user

        # Create Interaction with type 'system'
        interaction = Interaction.objects.create(
            user=request.user,
            contact=task.contact,
            interaction_type=Interaction.InteractionType.SYSTEM,
            sender=Interaction.SenderType.SYSTEM,
            description=f"Task complete: {task.task_type} - {task.target}",
            date=timezone.now(),
            chat=chat
        )

        # Create TasksMessage
        TasksMessage.objects.create(
            interaction=interaction,
            contact=task.contact,
            type=TasksMessage.Type.COMPLETE,
            task=task,
            created_at=timezone.now()
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

        return JsonResponse({
            'success': True,
            'contact_id': task.contact.id
        })
    except Task.DoesNotExist:
        logger.error(f"Task not found: id={task_id}, user={request.user.id}")
        return JsonResponse({'success': False, 'error': 'Задача не знайдена'}, status=404)
    except Exception as e:
        logger.error(f"Error in complete_task: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def confirm_new(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    context = {
        'contact': contact,
    }
    return render(request, 'tasks/task_confirm_new_modal.html', context)


@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == 'POST':
        data = request.POST.copy()
        data.setdefault('task_date', task.task_date.date().isoformat())
        data.setdefault('task_time', task.task_date.strftime('%H:%M'))
        form = TaskForm(data, instance=task, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Задачу відредаговано!')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('kanban_board')
            except ValueError as e:
                logger.error(f"Error in edit_task: {str(e)}", exc_info=True)
                messages.error(request, f'Помилка: {str(e)}')
        else:
            logger.error(f"Form errors in edit_task: {form.errors}")
            messages.error(request, 'Некоректні дані форми')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Некоректні дані форми',
                'errors': form.errors.as_json(),
                'labels': {name: field.label for name, field in form.fields.items()}
            }, status=400)
    else:
        form = TaskForm(instance=task, user=request.user)
    context = {
        'form': form,
        'task': task,
        'contact_id': task.contact.id,
    }
    return render(request, 'tasks/task_edit_modal.html', context)





@login_required
def transfer_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == 'POST':
        form = TaskTransferForm(request.POST, user=request.user, task=task)
        if form.is_valid():
            try:
                TaskTransfer.objects.create(
                    task=task,
                    reason=form.cleaned_data['reason'],
                    from_date=task.task_date,
                    to_date=form.cleaned_data['to_date'],
                )
                chat = Chat.objects.filter(user=request.user, contact=task.contact).first()
                user = request.user
                # Create Interaction with type 'system'
                interaction = Interaction.objects.create(
                    user=request.user,
                    contact=task.contact,
                    interaction_type=Interaction.InteractionType.SYSTEM,
                    sender=Interaction.SenderType.SYSTEM,
                    description=f"Task transfer: {task.task_type} - {task.target} з {task.task_date} на {form.cleaned_data['to_date']}",
                    date=timezone.now(),
                    chat=chat
                )

                # Create TasksMessage
                TasksMessage.objects.create(
                    interaction=interaction,
                    contact=task.contact,
                    type=TasksMessage.Type.COMPLETE,
                    task=task,
                    created_at=timezone.now()
                )
                task.task_date = form.cleaned_data['to_date']
                task.save()

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


                return JsonResponse({'success': True})
            except ValueError as e:
                logger.error(f"Error in transfer_task: {str(e)}, POST data: {request.POST}")
                return JsonResponse({'error': str(e)}, status=400)
        else:
            logger.error(f"Form errors in transfer_task: {form.errors}, POST data: {request.POST}")
            return JsonResponse({
                'error': 'Некоректні дані форми',
                'errors': form.errors.as_json(),
                'labels': {name: field.label for name, field in form.fields.items()}
            }, status=400)
    form = TaskTransferForm(user=request.user, task=task)
    context = {
        'form': form,
        'task': task,
    }
    return render(request, 'tasks/task_transfer_modal.html', context)


@login_required
@require_GET
def get_available_slots(request):
    date_str = request.GET.get('date')
    exclude_id = request.GET.get('exclude_task_id')
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        exclude_id = int(exclude_id) if exclude_id else None
        slots = Task.get_available_slots(date, request.user, exclude_task_id=exclude_id)
        return JsonResponse({'slots': [slot.strftime('%H:%M') for slot in slots]})
    except ValueError:
        logger.error(f"Invalid date format: {date_str}")
        return JsonResponse({'error': 'Невірний формат дати'}, status=400)


@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    context = {
        'task': task,
        'contact': task.contact,
    }
    return render(request, 'tasks/task_detail_modal.html', context)