import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Max
from django.template.loader import render_to_string

# Імпорти моделей залишаємо, оскільки asgi.py виправлено
from chats.models import Chat, Interaction
from contacts.models import Contact
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            print(f"WebSocket connect attempt: Anonymous user, closing connection")
            await self.close()
            return

        # Група для списку чатів користувача
        self.chats_group_name = f'user_{self.user.id}_chats'
        await self.channel_layer.group_add(self.chats_group_name, self.channel_name)
        print(f"WebSocket connected: Added to group {self.chats_group_name}")

        # Група для активного чату (chat_id передається в URL)
        self.chat_id = self.scope['url_route']['kwargs'].get('chat_id')
        if self.chat_id:
            self.chat_group_name = f'chat_{self.chat_id}'
            await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
            print(f"WebSocket connected: Added to group {self.chat_group_name}")

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'chats_group_name'):
            await self.channel_layer.group_discard(self.chats_group_name, self.channel_name)
            print(f"WebSocket disconnected: Removed from group {self.chats_group_name}")
        if hasattr(self, 'chat_group_name'):
            await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)
            print(f"WebSocket disconnected: Removed from group {self.chat_group_name}")

    async def receive(self, text_data):
        # Обробка повідомлень від клієнта
        print(f"WebSocket received message: {text_data}")
        pass

    # Обробка повідомлення про оновлення списку чатів
    async def update_chats(self, event):
        print(f"WebSocket sending update_chats event for user {self.user.id}")
        chats = await self.get_chats()
        await self.send(text_data=json.dumps({
            'type': 'update_chats',
            'chats': chats
        }))
        print(f"WebSocket sent update_chats with {len(chats)} chats")

    # Обробка повідомлення про нову взаємодію
    async def update_interaction(self, event):
        print(f"WebSocket sending update_interaction event for interaction {event['interaction_id']}")
        interaction_html = await self.get_interaction_html(event['interaction_id'])
        if interaction_html:
            await self.send(text_data=json.dumps({
                'type': 'update_interaction',
                'interaction_id': event['interaction_id'],
                'html': interaction_html
            }))
            print(f"WebSocket sent update_interaction with HTML for ID {event['interaction_id']}")
        else:
            print(f"Failed to send update_interaction: Interaction {event['interaction_id']} not found")

    async def open_call_result_modal(self, event):
        print(f"WebSocket sending open_call_result_modal for call {event['call_id']}")
        await self.send(text_data=json.dumps({
            'type': 'open_call_result_modal',
            'call_id': event['call_id'],
            'description': event.get('description', ''),
            'result': event.get('result', ''),
            'loading': event.get('loading', False)
        }))
        print(f"WebSocket sent open_call_result_modal for call ID {event['call_id']}")

    @database_sync_to_async
    def get_chats(self):
        # Сортуємо чати за останньою взаємодією або created_at
        chats = Chat.objects.filter(user=self.user).select_related('contact').annotate(
            last_interaction=Max('interactions__date')
        ).order_by('-last_interaction', '-created_at')
        chat_list = [{
            'id': chat.id,
            'contact_name': f"{chat.contact.first_name} {chat.contact.last_name or ''}",
            'company_name': chat.contact.company.name if chat.contact.company else '',
            'avatar': chat.contact.avatar.url if chat.contact.avatar else None,
        } for chat in chats]
        print(f"get_chats returned {len(chat_list)} chats for user {self.user.id}: {chat_list}")
        return chat_list

    @database_sync_to_async
    def get_interaction_html(self, interaction_id):
        try:
            interaction = Interaction.objects.filter(id=interaction_id).select_related('contact',
                                                                                       'contact_phone').prefetch_related(
                'viber_messages', 'calls', 'telegram_messages').first()
            if not interaction:
                print(f"Interaction {interaction_id} not found")
                return None
            # Рендеримо HTML із шаблону interaction_item.html
            html = render_to_string('chats/interaction_item.html', {'interaction': interaction})
            return html
        except Exception as e:
            print(f"Error rendering interaction {interaction_id}: {str(e)}")
            return None


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            print(f"WebSocket connect attempt: Anonymous user, closing connection")
            await self.close()
            return

        self.notifications_group_name = f'user_{self.user.id}_notifications'
        await self.channel_layer.group_add(self.notifications_group_name, self.channel_name)
        print(f"WebSocket connected: Added to group {self.notifications_group_name}")

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'notifications_group_name'):
            await self.channel_layer.group_discard(self.notifications_group_name, self.channel_name)
            print(f"WebSocket disconnected: Removed from group {self.notifications_group_name}")

    async def show_notification(self, event):
        print(f"WebSocket sending show_notification for chat {event['chat_id']}")
        await self.send(text_data=json.dumps({
            'type': 'show_notification',
            'chat_id': event['chat_id'],
            'contact_name': event['contact_name'],
            'company_name': event['company_name'],
            'message': event['message']
        }))
        print(f"WebSocket sent show_notification: {event}")