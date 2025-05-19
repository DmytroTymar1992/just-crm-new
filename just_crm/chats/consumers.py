import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Max

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
        interaction = await self.get_interaction(event['interaction_id'])
        await self.send(text_data=json.dumps({
            'type': 'update_interaction',
            'interaction': interaction
        }))
        print(f"WebSocket sent update_interaction: {interaction}")



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
    def get_interaction(self, interaction_id):
        interaction = Interaction.objects.filter(id=interaction_id).select_related('contact', 'contact_phone').first()
        if not interaction:
            print(f"Interaction {interaction_id} not found")
            return None
        result = {
            'id': interaction.id,
            'type': interaction.interaction_type,
            'sender': interaction.sender,
            'description': interaction.description,
            'date': interaction.date.strftime('%d.%m.%Y %H:%M'),
            'contact_phone': interaction.contact_phone.phone if interaction.contact_phone else None,
            'recording_link': interaction.calls.first().recording_link if interaction.interaction_type == 'call' and interaction.calls.exists() else None,
        }
        print(f"get_interaction returned for ID {interaction_id}: {result}")
        return result


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