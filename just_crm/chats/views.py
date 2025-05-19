from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from chats.models import Chat, Interaction
from contacts.models import Contact
from django.db.models import Max


@login_required
def chat_view(request, chat_id=None):
    # Сортуємо чати за датою останньої взаємодії або created_at
    chats = Chat.objects.filter(user=request.user).select_related('contact').annotate(
        last_interaction=Max('interactions__date')
    ).order_by('-last_interaction', '-created_at')
    selected_chat = None
    interactions = []
    if chat_id:
        selected_chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        interactions = Interaction.objects.filter(chat=selected_chat).select_related('contact', 'contact_phone',
                                                                                     'contact_email').order_by('date')

    context = {
        'chats': chats,
        'selected_chat': selected_chat,
        'interactions': interactions,
    }
    return render(request, 'chats/chat.html', context)


@login_required
def send_message(request, chat_id):
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