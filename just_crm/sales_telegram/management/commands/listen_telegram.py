import asyncio
from django.core.management.base import BaseCommand
from sales_telegram.matrix_utils import MatrixTelegramClient
from chats.models import Chat, Interaction
from contacts.models import Contact, ContactPhone
from sales_telegram.models import TelegramMessage, TelegramMessageMedia
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Listens for incoming Telegram direct messages via Matrix'

    def handle(self, *args, **options):
        async def message_callback(telegram_chat_id, message_id, sender, content):
            try:
                # Фільтруємо лише особисті чати (позитивний chat_id, не починається з '-')
                if telegram_chat_id.startswith('-'):
                    logger.debug(f"Ignoring group/channel message from {telegram_chat_id}")
                    return

                text = content.get('text', '')
                files = content.get('files', [])
                phone_number = f"+{telegram_chat_id}"
                logger.info(f"Processing direct message from {telegram_chat_id}")

                user = None
                contact = None
                contact_phone = None

                # Шукаємо користувача CRM за telegram_id
                user = await database_sync_to_async(lambda: User.objects.filter(telegram_id=telegram_chat_id).first())()
                if user:
                    logger.info(f"Found user {user.username}")
                    contact = await database_sync_to_async(lambda: Contact.objects.create(
                        first_name="Unknown", last_name=f"Telegram {telegram_chat_id}"
                    ))()
                    contact_phone = await database_sync_to_async(lambda: ContactPhone.objects.create(
                        contact=contact, phone=phone_number
                    ))()
                else:
                    user = await database_sync_to_async(lambda: User.objects.filter(is_superuser=True).first())()
                    if not user:
                        logger.error("No admin user found")
                        return
                    logger.info(f"No user found, assigning to admin: {user.username}")
                    contact = await database_sync_to_async(lambda: Contact.objects.create(
                        first_name="Unknown", last_name=f"Telegram {telegram_chat_id}"
                    ))()
                    contact_phone = await database_sync_to_async(lambda: ContactPhone.objects.create(
                        contact=contact, phone=phone_number
                    ))()

                chat, created = await database_sync_to_async(lambda: Chat.objects.get_or_create(
                    user=user, contact=contact, defaults={'created_at': timezone.now()}
                ))()

                interaction = await database_sync_to_async(lambda: Interaction.objects.create(
                    user=user, chat=chat, contact=contact, contact_phone=contact_phone,
                    interaction_type='telegram', sender='contact', description=text,
                    date=timezone.now(), is_read=False
                ))()

                message_type = 'mixed' if files else 'text'
                telegram_message = await database_sync_to_async(lambda: TelegramMessage.objects.create(
                    interaction=interaction, chat=chat, contact=contact, contact_phone=contact_phone,
                    telegram_chat_id=telegram_chat_id, message_id=message_id, message_type=message_type,
                    text=text, is_read=False
                ))()

                for file in files:
                    await database_sync_to_async(lambda: TelegramMessageMedia.objects.create(
                        telegram_message=telegram_message, media_type=file['type'],
                        file_url=file['file_url'], file_id=file['file_id']
                    ))()

                channel_layer = get_channel_layer()
                await channel_layer.group_send(
                    f'chat_{chat.id}', {'type': 'update_interaction', 'interaction_id': interaction.id}
                )
                await channel_layer.group_send(f'user_{user.id}_chats', {'type': 'update_chats'})
                await channel_layer.group_send(
                    f'user_{user.id}_notifications',
                    {
                        'type': 'show_notification', 'chat_id': chat.id,
                        'contact_name': f"{contact.first_name} {contact.last_name or ''}",
                        'company_name': contact.company.name if contact.company else '',
                        'message': 'Нове повідомлення в Telegram'
                    }
                )
                logger.info(f"Processed direct message from {telegram_chat_id} to user {user.id}")
            except Exception as e:
                logger.error(f"Error processing message from {telegram_chat_id}: {e}")

        matrix_client = MatrixTelegramClient()
        self.stdout.write(self.style.SUCCESS('Started listening for Telegram messages'))
        try:
            asyncio.run(matrix_client.start_listener(message_callback))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Stopped listening for Telegram messages'))