import asyncio
import re
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings

from channels.layers import get_channel_layer
from channels.db import database_sync_to_async

from sales_telegram.matrix_utils import MatrixTelegramClient
from chats.models import Chat, Interaction
from contacts.models import Contact, ContactPhone
from sales_telegram.models import TelegramMessage, TelegramMessageMedia

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Listens for incoming Telegram direct messages via Matrix"

    # ------------------------------------------------------------
    @staticmethod
    def _parse_sender(sender_str: str):
        m = re.match(r"^@telegram_(?P<tg_id>\d+)(?:_(?P<username>[^:]+))?:", sender_str)
        return (m.group("tg_id"), m.group("username")) if m else (None, None)

    # ------------------------------------------------------------
    def handle(self, *args, **options):
        async def message_callback(telegram_chat_id, matrix_event_id, sender, content):
            # --- CHANGE: єдиний id для перевірки/запису --------------
            telegram_msg_id = content.get("tgm_id") or matrix_event_id

            logger.debug(
                "⇢  DM │ matrix=%s │ tgm=%s │ chat_id=%s │ sender=%s",
                matrix_event_id,
                telegram_msg_id,
                telegram_chat_id,
                sender,
            )

            # дубль по справжньому telegram_msg_id
            if await database_sync_to_async(
                lambda: TelegramMessage.objects.filter(message_id=telegram_msg_id).exists()
            )():
                logger.debug("Skip duplicate telegram_msg_id %s", telegram_msg_id)
                return

            # приватний chat_id?
            if not telegram_chat_id.isdigit() or telegram_chat_id.startswith("-"):
                return

            text = content.get("text", "")
            files = content.get("files", [])
            telegram_user_id, telegram_username = self._parse_sender(sender)
            phone_number = f"+{telegram_chat_id}"

            # -------------------------------------------------- 1. користувач CRM (логіка без змін)
            localpart = sender.lstrip("@").split(":", 1)[0]
            user = await database_sync_to_async(
                lambda: User.objects.filter(telegram_id=telegram_user_id).first()
            )()
            sender_type = "user" if user else "contact"

            if not user and sender == settings.MATRIX_ADMIN_USERNAME:
                user = await database_sync_to_async(
                    lambda: User.objects.filter(username=localpart).first()
                )()
                sender_type = "user" if user else "contact"

            if not user:
                user = await database_sync_to_async(
                    lambda: User.objects.filter(is_superuser=True).first()
                )()
            if not user:
                logger.error("No fallback admin user, skip message %s", telegram_msg_id)
                return

            # -------------------------------------------------- 2. Contact + Phone (без змін)
            def get_contact_phone():
                q = (
                    ContactPhone.objects.filter(phone=phone_number)
                    | ContactPhone.objects.filter(telegram_id=telegram_chat_id)
                )
                if telegram_username:
                    q |= ContactPhone.objects.filter(telegram_username=telegram_username)
                return q.select_related("contact").first()

            contact_phone = await database_sync_to_async(get_contact_phone)()
            if contact_phone:
                contact = contact_phone.contact
            else:
                contact = await database_sync_to_async(
                    lambda: Contact.objects.create(
                        first_name="Unknown", last_name=f"Telegram {telegram_chat_id}"
                    )
                )()
                contact_phone = await database_sync_to_async(
                    lambda: ContactPhone.objects.create(
                        contact=contact,
                        phone=phone_number,
                        telegram_id=telegram_chat_id,
                        telegram_username=telegram_username,
                    )
                )()

            # -------------------------------------------------- 3. Chat (без змін)
            chat, _ = await database_sync_to_async(
                lambda: Chat.objects.get_or_create(
                    user=user, contact=contact, defaults={"created_at": timezone.now()}
                )
            )()

            # -------------------------------------------------- 4. Interaction (без змін)
            interaction = await database_sync_to_async(
                lambda: Interaction.objects.create(
                    user=user,
                    chat=chat,
                    contact=contact,
                    contact_phone=contact_phone,
                    interaction_type="telegram",
                    sender=sender_type,
                    description=text,
                    date=timezone.now(),
                    is_read=False,
                )
            )()

            # -------------------------------------------------- 5. TelegramMessage
            msg_type = "mixed" if files else "text"
            telegram_message = await database_sync_to_async(
                lambda: TelegramMessage.objects.create(
                    interaction=interaction,
                    chat=chat,
                    contact=contact,
                    contact_phone=contact_phone,
                    telegram_chat_id=telegram_chat_id,
                    message_id=telegram_msg_id,  # --- CHANGE
                    message_type=msg_type,
                    text=text,
                    is_read=False,
                )
            )()

            for f in files:
                await database_sync_to_async(
                    lambda: TelegramMessageMedia.objects.create(
                        telegram_message=telegram_message,
                        media_type=f["type"],
                        file_url=f["file_url"],
                        file_id=f["file_id"],
                    )
                )()

            logger.info("✓  Saved message %s (%s)", telegram_msg_id, sender_type)

            # -------------------------------------------------- 6. WebSocket push (без змін)
            layer = get_channel_layer()
            await layer.group_send(
                f"chat_{chat.id}",
                {"type": "update_interaction", "interaction_id": interaction.id},
            )
            await layer.group_send(f"user_{user.id}_chats", {"type": "update_chats"})
            await layer.group_send(
                f"user_{user.id}_notifications",
                {
                    "type": "show_notification",
                    "chat_id": chat.id,
                    "contact_name": f"{contact.first_name} {contact.last_name or ''}",
                    "company_name": contact.company.name if contact.company else "",
                    "message": "Нове повідомлення в Telegram",
                },
            )

        # ---------------- запуск слухача ----------------
        matrix_client = MatrixTelegramClient()
        self.stdout.write(self.style.SUCCESS("Started listening for Telegram messages"))
        try:
            asyncio.run(matrix_client.start_listener(message_callback))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopped listening for Telegram messages"))
